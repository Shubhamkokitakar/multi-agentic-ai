from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.websockets import WebSocket
import config.config as cfg 
from utils.logger import logger
from config.persona_summary import persona
from langchain_openai import AzureChatOpenAI
from config.capability_metadata import capability_metadata
from services.agent import Agent
from services.blob_service import AzureBlobHandler
from services.azure_index import AzureSearchHelper
from services.data_query_processor import SQLHelper, DataFormatter
from services.access_control import AccessControl
import concurrent.futures
from security.authentication_middleware import authentication_middleware
from concurrent.futures import ProcessPoolExecutor, as_completed
import asyncio
from typing import List, Dict
from pydantic import BaseModel
import multiprocessing

router = APIRouter()
router_ws = APIRouter()
search_helper = AzureSearchHelper(
    service_name=cfg.service_name,
)
access_control = AccessControl(cfg.client_id, cfg.client_secret, cfg.tenant_id)
blob_handler = AzureBlobHandler(
    account_name=cfg.storage_acc_name, account_key=cfg.storage_acc_key
)
sql_helper = SQLHelper()

class SmartPanelData(BaseModel):
    guid: List[str]
    query: List[str]

class SmartPanelPayload(BaseModel):
    user_email: str
    data: SmartPanelData

class GetPersona(BaseModel):
    email: str
    group_dict: List[Dict[str, str]]
    
def process_query_with_guid(index: int, guid: str, query: str):
    try:
        df = sql_helper.execute_sql_query(query, "")

        df,all_columns,numerical_columns = DataFormatter.clean_and_format_df(df)
       
        logger.info(f"Processed guid={guid}, query={query}, rows={len(df) if df else 0}")
        
        return index, guid, query, df,all_columns,numerical_columns
    except Exception as e:
        logger.error(f"Error processing query for guid {guid}: {e}")
        return index, guid, query, None, None, None

@router.post("/get-smart-panel-data")
def get_smart_panel_data(payload: SmartPanelPayload):
    logger.info(f"Received request from user: {cfg.html.escape(str(payload.user_email))}")
    queries = payload.data.query
    guids = payload.data.guid

    if len(queries) != len(guids):
        return {"error": "guid and query lists must be of the same length"}

    max_workers = min(len(queries), multiprocessing.cpu_count())
    results = [None] * len(queries)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_query_with_guid, i, guids[i], queries[i])
            for i in range(len(queries))
        ]

        for future in as_completed(futures):
            index, guid, query, df,all_columns,numerical_columns = future.result()
            results[index] = {"guid": guid, "query": query, "graph_data": df,"availableColumns":all_columns,"numericalColumns":numerical_columns}
    return results



@router.get("/")
def read_root():
    """
    Executes a default SQL query to trigger compute startup.

    Returns:
        dict: A greeting message and a sample dataframe result from the query.
    """
    query = "SELECT TOP 1 SupplierName FROM IntegratedAnalytics.CombinedSpend WHERE L3ShortBU = 'MCBU';"
    df = sql_helper.execute_sql_query(query, "")
    return {"message": "Hello World", "df": df}

@router.get("/webapp")
def webapp():
    """
    Redirects to the specified app URL.
    """
    return RedirectResponse(url=cfg.appUrl)


@router.post("/define-persona")
def get_persona(request: GetPersona):
    try:
        user_info = access_control.search_azure_users(request.email, save_flag=True)
        if isinstance(user_info, str):
            raise HTTPException(status_code=404, detail=f"User not found: {user_info}")
        if not user_info or not user_info[0].get("jobTitle"):
            raise HTTPException(status_code=400, detail="Job title not found for user")

        jobTitle = user_info[0]["jobTitle"]
        user_id = access_control.get_user_id(request.email)

        credential = cfg.DefaultAzureCredential()
        cfg.os.environ["AZURE_OPENAI_AD_TOKEN"] = credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token

        llm = AzureChatOpenAI(
            temperature=0,
            azure_deployment="gpt-4_1-gs-2025-04-14",
            azure_endpoint=cfg.AZURE_OPENAI_ENDPOINT,
            api_version="2024-04-01-preview",
            default_headers={"Content-Type": "application/json"},
            max_tokens=32768,
            timeout=None,
            max_retries=2,
            top_p=1.0,
        )

        agent = Agent(llm=llm)
        AzureChatOpenAI.model_rebuild()

        agent_definition = capability_metadata.get("$agents")
        if not agent_definition or "PersonadeFiner" not in agent_definition:
            raise HTTPException(status_code=500, detail="Agent definition missing")

        group_id, output_tokens, input_tokens = agent.run_agent_chain(
            question=jobTitle,
            agent_definition=agent_definition["PersonadeFiner"],
            system_inputs={"group_ids": request.group_dict}
        )

        access_control.add_user_to_group(group_id, user_id)
        return {"Persona Updated Sucessfully"}

    except HTTPException as http_err:
        raise http_err
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error")


@router_ws.websocket("/get-ai-response")
async def get_ai_response(websocket: WebSocket):
    """
    WebSocket endpoint with manual JWT authentication for AI-powered question answering.
    
    Authentication is handled manually since WebSocket connections don't support
    FastAPI's standard dependency injection pattern.
    """
    logger.info("WebSocket connection attempt initiated")
    
    # Extract token from query parameters
    access_token = websocket.query_params.get("access_token")
    
    if not access_token:
        logger.warning("WebSocket connection rejected: Missing access token")
        await websocket.close(code=4001, reason="Missing access token")
        return
    
    # Validate the token manually
    try:
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=access_token
        )
        
        token_payload = await authentication_middleware.verify_token(mock_credentials)
        
        user_info = {
            "user_id": token_payload.get("oid"),
            "username": token_payload.get("preferred_username"),
            "email": token_payload.get("upn") or token_payload.get("preferred_username"),
            "groups": token_payload.get("groups", []),
            "name": token_payload.get("name")
        }
        
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {str(e)}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    logger.info("WebSocket Initialized")
    websocket_open = True
    await websocket.accept()
    logger.info("WebSocket connected")
    data = await websocket.receive_text()
    request = cfg.json.loads(data)
    messages = request.get("messages")
    latest_question = messages[-1]
    question = latest_question.get("text")
    persona_name = latest_question.get("userRole")
    chat_history = messages[-4:]
    chat_history = [
        {"text": item["text"], "type": item["type"], "query": item.get("query", None)}
        for item in chat_history
        if not (item["type"] == "app" and item["tag"] != "")
    ]
    credential = cfg.DefaultAzureCredential()
    cfg.os.environ["AZURE_OPENAI_AD_TOKEN"] = credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token
    llm = AzureChatOpenAI(
        temperature=0,
        azure_deployment="gpt-4_1-gs-2025-04-14",
        azure_endpoint=cfg.AZURE_OPENAI_ENDPOINT,
        api_version="2024-04-01-preview",
        default_headers={"Content-Type": "application/json"},
        max_tokens=32768,
        timeout=None,
        max_retries=2,
        top_p=1.0,
    )
   
    agent = Agent(llm=llm)
    AzureChatOpenAI.model_rebuild()
    schemas = {
        key: capability_metadata[key] for key in ["$schema"]
    }
    joins={ key: capability_metadata[key] for key in ["joins"]}
    agent_definition = capability_metadata.get("$agents")
    capabilities = capability_metadata.get("$Capabilities")
    persona_summary = persona[persona_name]
    (
        feedback,
        query,
        flag,
        supplier_flag,
        agent_response,
        CongressionalDistrict_flag,
    ) = (None, "", True, False, None, False)
    graph_query, table_query = None, None
    analytical_question_table = None
    schema = None
    graphs = None
    sample_queries = None
    sample_queries2 = None
    reinforcement_flag = ""
    await websocket.send_json(
        {
            "tag": "<h3>Interpreting your question...</h3>",
            "data": {},
            "query": "",
        }
    )
    if persona_name == "Congress Spend Analyst" and any(
        keyword in question.lower()
        for keyword in [
            "congress",
            "congressional",
            "congressional district",
            "district",
            "districts",
        ]
    ):
        CongressionalDistrict_flag = True
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.max_workers) as executor:
        # Run EntityFinder and QuestionAnalyzer in parallel
        entity_finder_future = executor.submit(
            agent.extract_entities,
            question=question,
            agent_definition=agent_definition.get("EntityFinder"),
            CongressionalDistrict_flag=False,
        )
        question_analyzer_future = executor.submit(
            agent.run_agent_chain,
            question=question,
            agent_definition=agent_definition.get("QuestionAnalyzer"),
            system_inputs={"chat_history": chat_history},
        )

        # Wait for both functions to complete and collect their results
        concurrent.futures.wait([entity_finder_future, question_analyzer_future])
        (
            taxonomy_list,
            bu_geographics_list,
            rig_name_list,
            suppliers,
            congress_spend_list,
            units_list,
            csid_list,
            output_tokens_,
            input_tokens_,
        ) = entity_finder_future.result()
        cfg.input_tokens += input_tokens_
        cfg.output_tokens += output_tokens_

        (
            analytical_question,
            output_tokens_,
            input_tokens_,
        ) = question_analyzer_future.result()
        cfg.input_tokens += input_tokens_
        cfg.output_tokens += output_tokens_

    if suppliers != ["Use the LIKE keyword for querying"] and suppliers != []:
        supplier_flag = True
    # return the responce and close the websocket if general question is asked
    if analytical_question.startswith("G"):
        await websocket.send_json(
            {
                "tag": analytical_question.replace("G:", ""),
                "data": {},
                "query": "",
            }
        )
        await websocket.close()
        websocket_open = False

    else:
        analytical_question_list = analytical_question.replace("Q:", "").strip()
        logger.info(analytical_question_list)
        try:
            analytical_question_list = cfg.ast.literal_eval(analytical_question_list)

            if len(analytical_question_list) == 2:
                analytical_question, analytical_question_table = analytical_question_list
                sample_queries = search_helper.query_retriever(
                    analytical_question, cfg.query_reinforcement_graph_index
                )
                sample_queries2 = search_helper.query_retriever(
                    analytical_question_table, cfg.query_reinforcement_table_index
                )
                await websocket.send_json(
                    {
                        "tag": f"<h3>Formulating the Search Spell for:</h3><p>{analytical_question}</p>",
                        "data": {},
                        "query": "",
                        "analytical_question_graph": analytical_question,
                        "analytical_question_table": analytical_question_table,
                    }
                )
            else:
                analytical_question = analytical_question_list[0]
                sample_queries = search_helper.query_retriever(
                    analytical_question, cfg.query_reinforcement_graph_index
                )
        except: 
            analytical_question = analytical_question_list
            sample_queries = search_helper.query_retriever(
                analytical_question, cfg.query_reinforcement_graph_index
            )

            await websocket.send_json(
                {
                    "tag": f"<h3>Formulating the Search Spell for:</h3><p>{analytical_question}</p>",
                    "data": {},
                    "query": "",
                    "analytical_question_graph": analytical_question,
                }
            )
        

        if CongressionalDistrict_flag:
            schema = {}
            schema_name = "IntegratedAnalytics.CongressionalDistrict"
        else:
            schema = {}
            schema["$schema"] = {
                key: value
                for key, value in capability_metadata["$schema"].items()
                if key != "IntegratedAnalytics.CongressionalDistrict"
            }

            schema_name, input_tokens_, output_tokens_ = agent.run_agent_chain(
                question=analytical_question,
                agent_definition=agent_definition.get("SchemaSelector"),
                system_inputs={"chat_history": chat_history, "Schema": schema},
            )
        schema["$schema"] = {}
        matched_capabilities = {}
        schema_names = schema_name.replace("IntegratedAnalytics.", "").split(",")
        for table in schema_names:
            key = "CombinedSpend" if table in ["CombinedSpend", "RigCost"] else table
            capability = capabilities.get(key, "")
            schema["$schema"][f"IntegratedAnalytics.{table}"] = capability_metadata["$schema"].get(f"IntegratedAnalytics.{table}", {})
            if capability:
                matched_capabilities[f"IntegratedAnalytics.{table}"]=(capability)

        join_condition = (
        joins["joins"].get("multiple_schema", "")
        if len(schema_names) > 1
        else joins["joins"].get("single_schema", "")
        )
        cfg.input_tokens += input_tokens_
        cfg.output_tokens += output_tokens_
        sample_queries = { k: v for k, v in sample_queries.items() if schema_name in v.replace('"', '')}if sample_queries else {}
        sample_queries2 = { k: v for k, v in sample_queries2.items() if schema_name in v.replace('"', '')}if sample_queries2 else {}
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.max_workers) as executor:
            futures = []
            if analytical_question_table:
                # Submit both queries to run in parallel
                futures.append(
                    executor.submit(
                        asyncio.run,
                        generate_query_with_feedback(
                            query,
                            feedback,
                            flag,
                            analytical_question,
                            agent,
                            agent_definition,
                            schema,
                            chat_history,
                            supplier_flag,
                            taxonomy_list,
                            bu_geographics_list,
                            rig_name_list,
                            sample_queries,
                            congress_spend_list,
                            units_list,
                            csid_list,
                            matched_capabilities,
                            join_condition,
                            schema_name,
                            "QueryGenerator",
                            joins=joins
                        ),
                    )
                )

                futures.append(
                    executor.submit(
                        asyncio.run,
                        generate_query_with_feedback(
                            query,
                            feedback,
                            flag,
                            analytical_question_table,
                            agent,
                            agent_definition,
                            schema,
                            chat_history,
                            supplier_flag,
                            taxonomy_list,
                            bu_geographics_list,
                            rig_name_list,
                            sample_queries2,
                            congress_spend_list,
                            units_list,
                            csid_list,
                            matched_capabilities,
                            join_condition,
                            schema_name,
                            "QueryGenerator",
                            pivot_logic=capabilities.get("Time Period Handling"),
                            joins=joins
                        ),
                    )
                )
            else:
                # Only run for analytical_question if analytical_question_table doesn't exist
                futures.append(
                    executor.submit(
                        asyncio.run,
                        generate_query_with_feedback(
                            query,
                            feedback,
                            flag,
                            analytical_question,
                            agent,
                            agent_definition,
                            schema,
                            chat_history,
                            supplier_flag,
                            taxonomy_list,
                            bu_geographics_list,
                            rig_name_list,
                            sample_queries,
                            congress_spend_list,
                            units_list,
                            csid_list,
                            matched_capabilities,
                            join_condition,
                            schema_name,
                            "QueryGenerator",
                            joins=joins,
                        ),
                    )
                )

            # Wait for all futures to complete and get the results
            results = []
            for future in futures:
                try:
                    result = future.result()  # Get the result of each future
                    results.append(result)
                except Exception as e:
                    # Log the error and append default values for this future
                    logger.error(f"Error executing query: {e}")

            # Unpack results, handling failures if any of the futures failed
            
            if len(results) > 1:
                graph_query = results[0] if results[0] else None
                table_query = results[1] if results[1] else None
            elif len(results) == 1:
                graph_query = results[0] if results[0] else None
            else:
                await websocket.send_json({
                    "tag": "Looks like there are no records in my database that match your question. If you think this is a mistake, please rephrase your question"
                })
                await websocket.close()

                websocket_open = False
                return "WebSocket is closed. Stopping further execution."

        if websocket_open:
            if (
                table_query is not None
                and graph_query is not None
                and "not part of the capability" in table_query.lower()
                and "not part of the capability" in graph_query.lower()
            ):
                logger.info(f"Query '{query}', closing connection.")
                await websocket.send_json(
                    {
                        "tag": table_query,
                        "data": {},
                        "query": "",
                    }
                )
                await websocket.close()
                websocket_open = False
                return "WebSocket is closed. Stopping further execution."
            else:
                await websocket.send_json(
                    {
                        "tag": "<h3>Gathering the Results...</h3><p>Note: The main source of truth data for the tool is <strong>Combined Spend</strong>. Answers will be based on <strong>Combined Spend</strong>. For more information, refer to the <strong>Data Source</strong> tab on the top right.</p>",
                        "graph_query": graph_query,
                        "table_query": table_query,
                    }
                )
                try:
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=cfg.max_workers
                    ) as executor:
                        futures = []
                        future_to_task = {}

                        # Conditionally submit SQL queries
                        if graph_query is not None:
                            execute_sql_queryThread1 = executor.submit(
                                sql_helper.execute_sql_query, graph_query, suppliers
                            )
                            futures.append(execute_sql_queryThread1)
                            future_to_task[execute_sql_queryThread1] = "graph_query"

                        if table_query is not None:
                            execute_sql_queryThread2 = executor.submit(
                                sql_helper.execute_sql_query, table_query, suppliers
                            )
                            futures.append(execute_sql_queryThread2)
                            future_to_task[execute_sql_queryThread2] = "table_query"

                        # Submit agent tasks and create aliases
                        FollowUpQSuggestorThread = executor.submit(
                            agent.run_agent_chain,
                            question=analytical_question,
                            agent_definition=agent_definition.get(
                                "FollowUpQSuggestor"
                            ),
                            system_inputs={
                                "schema": schema,
                                "query": graph_query,
                                "chat_history": chat_history,
                                "persona": persona,
                            },
                        )
                        futures.append(FollowUpQSuggestorThread)
                        future_to_task[FollowUpQSuggestorThread] = (
                            "FollowUpQSuggestor"
                        )

                        GraphSuggestorThread = executor.submit(
                            agent.run_agent_chain,
                            question=analytical_question,
                            agent_definition=agent_definition.get("GraphSuggestor"),
                            system_inputs={"schema": schema, "query": graph_query},
                        )
                        futures.append(GraphSuggestorThread)
                        future_to_task[GraphSuggestorThread] = "GraphSuggestor"

                        # Initialize results variables
                        df1, df2 = None, None

                        # Process results
                        for future in concurrent.futures.as_completed(futures):
                            try:
                                task = future_to_task.get(future)

                                if task == "graph_query":
                                    df1 = future.result()
                                    if df1 is None:
                                        logger.warning(
                                            "SQL Query for graph returned no result."
                                        )
                                elif task == "table_query":
                                    df2 = future.result()
                                    if df2 is None:
                                        logger.warning(
                                            "SQL Query for table returned no result."
                                        )
                                elif task == "FollowUpQSuggestor":
                                    (
                                        follow_up_questions,
                                        input_tokens_,
                                        output_tokens_,
                                    ) = future.result()
                                    cfg.input_tokens += input_tokens_
                                    cfg.output_tokens += output_tokens_
                                    follow_up_questions=cfg.ast.literal_eval(follow_up_questions)
                                elif task == "GraphSuggestor":
                                    graphs, input_tokens_, output_tokens_ = (
                                        future.result()
                                    )
                                    cfg.input_tokens += input_tokens_
                                    cfg.output_tokens += output_tokens_

                            except Exception as e:
                                logger.error(f"Error processing future: {e}")
                    # Process results if successful
                    response = "No data available"
                    dfs = {}
                    apply_currency_flags = {}

                    # Use pd.DataFrame to ensure type checking
                    if (
                        isinstance(df1, cfg.pd.DataFrame)
                        and not df1.empty
                        and isinstance(df2, cfg.pd.DataFrame)
                        and not df2.empty
                    ):
                        dfs = {"graph_json": df1, "table_json": df2}
                        apply_currency_flags = {
                            "graph_json": False,
                            "table_json": True,
                        }
                        reinforcement_flag = "both"
                    elif isinstance(df1, cfg.pd.DataFrame) and not df1.empty:
                        dfs = {"graph_json": df1, "table_json": df1}
                        apply_currency_flags = {
                            "graph_json": False,
                            "table_json": True,
                        }
                        reinforcement_flag = "graph"
                    elif isinstance(df2, cfg.pd.DataFrame) and not df2.empty:
                        dfs = {"graph_json": df2, "table_json": df2}
                        apply_currency_flags = {
                            "graph_json": False,
                            "table_json": True,
                        }
                        reinforcement_flag = "table"
                    else:
                        response = "Looks like there are no records in my database that match your question. If you think this is a mistake, please rephrase your question."
                        await websocket.send_json({"tag": response})
                        await websocket.close()
                        websocket_open = False
                        return "WebSocket is closed. Stopping further execution."
                    # Submit formatting jobs if dfs is populated
                    if dfs:
                        with ProcessPoolExecutor(
                            max_workers=cfg.max_workers
                        ) as executor:
                            futures = {
                                name: executor.submit(
                                    DataFormatter.clean_and_format_df,
                                    df,
                                    apply_currency_flags[name],
                                )
                                for name, df in dfs.items()
                            }

                        results = {}
                        for name, future in futures.items():
                            try:

                                results[name] = future.result()
                            except Exception as e:
                                logger.error(f"Error processing {name}: {e}")

                                results[name] = None
                    else:
                        response = "Looks like there are no records in my database that match your question. If you think this is a mistake, please rephrase your question."
                        await websocket.send_json({"tag": response})
                        await websocket.close()
                        websocket_open = False
                        return "WebSocket is closed. Stopping further execution."
                except Exception as e:
                    logger.error(
                        f"Something went wrong during execution\nError: {e}"
                    )
                    response = "We are unable to process this information as of now, please rephrase your question or reach out to support"
                    await websocket.send_json({"tag": response})
                    await websocket.close()
                    websocket_open = False
                    return "WebSocket is closed. Stopping further execution."
                if websocket_open:
                    if len(results) == 1:
                        data = next(iter(results.values()))
                        await websocket.send_json(
                            {
                                "table_data": data,
                                "graph_data": data,
                                "SuggestedQuestions": follow_up_questions.get("follow_up_questions",[]),
                                "query_summary": follow_up_questions.get("query_summary",""),
                                "graphs": graphs,
                            }
                        )
                    else:
                        await websocket.send_json(
                            {
                                "table_data": results["table_json"],
                                "graph_data": results["graph_json"],
                                "SuggestedQuestions": follow_up_questions.get("follow_up_questions",[]),
                                "query_summary": follow_up_questions.get("query_summary",""),
                                "graphs": graphs,
                                "reinforcement_flag": reinforcement_flag,
                            }
                        )
                    try:
                        result, data_desc = DataFormatter.generate_data_profile(
                            df2 if df2 is not None and not df2.empty else df1
                        )

                        try:
                            data_desc = data_desc[:200]
                        except Exception as e:
                            logger.info(f"Error occurred: {e}")

                        # Prepare response
                        if isinstance(result, cfg.pd.DataFrame) and not result.empty:
                            response = result.head(200).to_dict(orient="records")
                        else:
                            fallback_df = (
                                df2 if df2 is not None and not df2.empty else df1
                            )
                            response = fallback_df.head(200).to_dict(
                                orient="records"
                            )

                    except Exception as e:
                        logger.info(f"Error occurred: {e}")
                        response = []
                    agent_response, output_tokens_, input_tokens_ = (
                        agent.run_agent_chain(
                            question=analytical_question,
                            agent_definition=agent_definition.get("DataSummarizer"),
                            system_inputs={
                                "data_description": data_desc,
                                "data": response,
                                "persona_summary": persona_summary,
                            },
                        )
                    )
                    cfg.output_tokens += output_tokens_
                    cfg.input_tokens += input_tokens_
                    await websocket.send_json(
                        {
                            "response": agent_response,
                        }
                    )
                    await websocket.close()
                    websocket_open = False
        try:
            if table_query or graph_query:

                guid = latest_question.get("guid",None) 
                if not guid:
                    raise ValueError("GUID not found in messages[0]. Please ensure messages list is seeded with a guid.")


                cost = (cfg.input_tokens * 2.0 / 1e6) + (cfg.output_tokens * 8.0 / 1e6)

                message = {
                    "analyticalquestion": analytical_question,
                    "query": table_query if table_query else graph_query,
                    "persona": persona_name,
                    "username": request.get("userName"),
                    "email": request.get("userEmail"),
                    "input_tokens": cfg.input_tokens,
                    "output_tokens": cfg.output_tokens,
                    "cost": cost,
                }
                col = ["GUID", "Messages", "Date"]
                guid_name = f"{guid}.json"

                try:
                    userlog_df = blob_handler.read_blob(cfg.userlog_blob_container_name, guid_name)
                    userlog_df = userlog_df[col]

                except Exception as e:
                    logger.error(f"Blob doesn't exist or doesn't have the right structure: {e}")
                    userlog_df = cfg.pd.DataFrame(columns=col)

                now_str = str(cfg.dt.datetime.now())
                msg_str = cfg.json.dumps(message, ensure_ascii=False)

                if (len(userlog_df) > 0) and (guid in set(userlog_df["GUID"].astype(str))):
                    logger.info("History exists, overwrite")
                    mask = userlog_df["GUID"].astype(str) == str(guid)
                    userlog_df.loc[mask, "Messages"] = msg_str
                    userlog_df.loc[mask, "Date"] = now_str
                else:
                    userlog_df.loc[len(userlog_df)] = [guid, msg_str, now_str]
                blob_handler.upload_blob(userlog_df, cfg.userlog_blob_container_name, guid_name)
                logger.info("User Logs Updated successfully")

                logger.info(
                    f"Output_tokens Used: {cfg.output_tokens} \tInput tokens used: {cfg.input_tokens}"
                )
                logger.info(f"Total Cost: {cost}")

            else:
                logger.info("Skipping user log update as table_query or graph_query is null/empty.")

        except Exception as e:
            logger.warning(f"User Logs Failed to Update: {e}")

    

async def generate_query_with_feedback(
    query,
    feedback,
    flag,
    analytical_question,
    agent,
    agent_definition,
    schema,
    chat_history,
    supplier_flag,
    taxonomy_list,
    bu_geographics_list,
    rig_name_list,
    sample_queries,
    congress_spend_list,
    units_list,
    csid_list,
    matched_capabilities,
    join_condition,
    schema_name,
    generator_agent,
    pivot_logic=None,
    joins=None
):
    """
    Refines an initial SQL query using feedback-based reinforcement loops.

    Args:
        query (str): Initial generated SQL query.
        feedback (str): Feedback from the critique agent.
        flag (bool): Flag to control loop execution.
        analytical_question (str): Original user question.
        agent (Agent): Agent instance to run agent chains.
        agent_definition (dict): Definitions of available agents.
        schema (dict): Schema metadata.
        chat_history (list): List of prior conversation messages.
        supplier_flag (bool): Flag indicating supplier-specific logic.
        taxonomy_list (list): List of taxonomy terms.
        bu_geographics_list (list): List of business unit geographics.
        rig_name_list (list): List of rig names.
        sample_queries (list): List of example queries.
        congress_spend_list (list): List of congress-related spend filters.
        units_list (list): List of units used in queries.
        csid_list (list): List of CSIDs used for filtering.
        matched_capabilities (dict): Dictionary of matched_capabilities metadata.
        schema_name (str): Name of the schema.
        generator_agent (str): Key name of the generator agent in agent_definition.

    Returns:
        tuple: Final query (str)
    """
    loop = 0
    while flag and loop < 2:

        query, output_tokens_, input_tokens_ = agent.run_agent_chain(
            question=analytical_question,
            agent_definition=agent_definition.get(f"{generator_agent}"),
            system_inputs={
                "join_condition":join_condition,
                "Capability": matched_capabilities,
                "schema": schema,
                "chat_history": chat_history,
                "feedback": feedback,
                "query": query,
                "supplier_flag": supplier_flag,
                "taxonomy_list": taxonomy_list,
                "bu_geographics_list": bu_geographics_list,
                "rig_name_list": rig_name_list,
                "sample_queries": sample_queries,
                "congress_spend_list": congress_spend_list,
                "units_list": units_list,
                "csid_list": csid_list,
                "pivot_logic":pivot_logic,
                "schema_names":schema_name,
                "date":str(cfg.dt.datetime.now().strftime("%Y-%m-%d")) if pivot_logic is not None else None,
                "what_if":capability_metadata.get("$Capabilities", {}).get("WhatIf", "") if analytical_question.lower().startswith("what if") else ""
            },
        )

        logger.info(query)
        cfg.output_tokens += output_tokens_
        cfg.input_tokens += input_tokens_

        if "not part of the capability" in query.lower():

            flag = False
        else:
            feedback, output_tokens_, input_tokens_ = agent.run_agent_chain(
                question=analytical_question,
                agent_definition=agent_definition.get("critique"),
                system_inputs={
                    "query": query,
                    "schema": schema,
                    "feedback": feedback,
                    "supplier_flag": supplier_flag,
                    "Capability": matched_capabilities,
                    "join_condition":join_condition,
                    "date": str(cfg.dt.datetime.now().strftime("%Y-%m-%d")),
                    "what_if":capability_metadata.get("$Capabilities", {}).get("WhatIf", "") if analytical_question.lower().startswith("what if") else ""
                },
            )
            if (
                "the query adheres to the guidelines and standards provided."
                in feedback.lower()
            ):
                flag = False
            cfg.output_tokens += output_tokens_
            cfg.input_tokens += input_tokens_
            loop += 1
            logger.info(f"Feedback from Critique: {feedback}")

    if flag:
        logger.warning(f"Feedback from critique not implemented successfully")

    return query