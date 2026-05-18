from fastapi import APIRouter, Depends, HTTPException
from config.config import *
from utils.logger import logger
from typing import List, Optional,Dict,Any
from services.blob_service import AzureBlobHandler
from services.access_control import AccessControl
from pydantic import BaseModel
import pandas as pd
import os
import multiprocessing
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor, as_completed
from services.data_query_processor import SQLHelper, DataFormatter
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from security.authentication_middleware import require_admin_group

router = APIRouter()

blob_handler = AzureBlobHandler(account_name=storage_acc_name, account_key=storage_acc_key)
access_control = AccessControl(client_id, client_secret, tenant_id)
sql_helper = SQLHelper()


class SmartPanelData(BaseModel):
    guid: List[str]
    title:Optional[List[str]]=None
    query: List[str]
    graph_suggestions: Optional[Dict[str, Any]]=None 
    table_data: List[List[Any]]
    selected_type: Optional[Dict[str, str]]=None
    selectedGraphIndices: Optional[Dict[str, Any]]=None
    active_view: Optional[Dict[str, str]]=None

class SmartPanelPayload(BaseModel):
    user_email: str
    operation: str
    date:Optional[str]=None
    data: Optional[SmartPanelData] = None

class HistoryPayload(BaseModel):
    user_email: str
    operation: str
    history: List[dict]
    message: List[dict]  
    
class DefaultGraphRequest(BaseModel):
    dashboard_name: str
    BU: str
    

def handle_api_error(message: str, status_code: int = HTTP_500_INTERNAL_SERVER_ERROR) -> HTTPException:
    logger.error(f"API Error: [{html.escape(message.replace(chr(10), ' ').replace(chr(13), ' '))}]")    
    return HTTPException(status_code=status_code, detail=message)

def process_query_with_guid(index: int, guid: str, query: str,title: str, graph_suggestions: str,table_data: str, active_view:str, selected_type:str,selectedGraphIndices):
    try:
        df = sql_helper.execute_sql_query(query, "")
        df = DataFormatter.clean_and_format_df(df)
        logger.info(f"Processed guid={guid}, query={query}, rows={len(df) if df is not None else 0}")
        return index, guid, query,title, graph_suggestions, table_data, df,selected_type, active_view, selectedGraphIndices
    except Exception as e:
        raise handle_api_error(f"Error processing query for guid {guid}: {e}")
def process_queries_in_parallel(
    guids: List[str],
    queries: List[str],
    graph_suggestions=None,
    table_data=None,
    active_view=None,
    selected_type=None,
    title=None,
    date=None,
    selectedGraphIndices=None,
):
    if len(queries) != len(guids):
        raise handle_api_error("guid and query lists must be of the same length", HTTP_400_BAD_REQUEST)

    max_workers = min(len(queries), multiprocessing.cpu_count())
    results = [None] * len(queries)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_query_with_guid,
                i,
                guids[i],
                queries[i],
                title[i]if title is not None else None,
                graph_suggestions.get(guids[i])  if graph_suggestions is not None else None,
                table_data[i]if table_data is not None else None,
                active_view.get(guids[i])  if active_view is not None else None,
                selected_type.get(guids[i]) if selected_type is not None else None,
                selectedGraphIndices.get(guids[i]) if selectedGraphIndices is not None else None
            )
            for i in range(len(queries))
        ]

        for future in as_completed(futures):
            index, guid, query, title, graph_suggestion, table_data_item, df, selected_type_item, active_view_item,selectedGraphIndices = future.result()
            results[index] = {
                "guid": guid,
                "query": query,
                "title":title if title is not None else None,
                "table_data": table_data_item,
                "graph_data": df,
                "graph_suggestions": {guid:graph_suggestion}if graph_suggestion is not None else None,
                "selected_type": {guid:selected_type_item}if selected_type_item is not None else None,
                "active_view": {guid:active_view_item}if active_view_item is not None else None,
                "date":date,
                "selectedGraphIndices": {guid:selectedGraphIndices}
            }

    return results

def extract_json(metadata):
    if isinstance(metadata, pd.DataFrame):
        if metadata.empty:
            return {}
        return metadata.iloc[0].to_dict()
    elif isinstance(metadata, dict):
        return metadata
    return {}

@router.post("/custom_graph")
def custom_graph(request: SmartPanelPayload):
    user_id = access_control.get_user_id(request.user_email)
    container_name = history_storage_container_name
    metadata_blob_name = f"metadata/{user_id}.json"

    existing_metadata = blob_handler.read_blob(container_name, metadata_blob_name)
    existing_json = extract_json(existing_metadata)

    if request.operation == "get":
        if not existing_json:
            return "No metadata found for the user."

        graph_data = existing_json.get("graph_data", [])
        guids = [entry["guid"] for entry in graph_data]
        queries = [entry["query"] for entry in graph_data]
        graph_suggestions = {entry["guid"]: entry.get("graph_suggestions", "") for entry in graph_data}
        table_data = [entry.get("table_data", "") for entry in graph_data]
        selected_type = {entry["guid"]: entry.get("selected_type", "") for entry in graph_data}
        selectedGraphIndices = {entry["guid"]: entry.get("selectedGraphIndices", "") for entry in graph_data}
        active_view = {entry["guid"]: entry.get("active_view", "") for entry in graph_data}
        title = [entry["title"] for entry in graph_data]
        date =existing_json.get("date", "")
        if not guids:
            return "No metadata found for the user."
        return process_queries_in_parallel(guids, queries, graph_suggestions, table_data, active_view, selected_type, title, date,selectedGraphIndices)

    elif request.operation == "save":
        
        graph_suggestions = request.data.graph_suggestions or {}
        selected_type = request.data.selected_type or {}
        active_view = request.data.active_view or {}
        selectedGraphIndices = request.data.selectedGraphIndices or {}
        title_list = request.data.title or [""] * len(request.data.guid)
        new_entries = [
            {
                "guid": g,
                "title": t,
                "query": q,
                "graph_suggestions": [
                    s.dict() if hasattr(s, "dict") else s
                    for s in graph_suggestions.get(g, [])
                ] if isinstance(graph_suggestions.get(g, []), list) else (
                    graph_suggestions.get(g).dict()
                    if hasattr(graph_suggestions.get(g), "dict")
                    else graph_suggestions.get(g, "")
                ),
                "table_data": td,
                "selected_type": selected_type.get(g, ""),
                "active_view": active_view.get(g, ""),
                "selectedGraphIndices":selectedGraphIndices.get(g, ""),
            }
            for g, q, td, t in zip(request.data.guid, request.data.query, request.data.table_data, title_list)
        ]

        graph_data_dict = {entry["guid"]: entry for entry in existing_json.get("graph_data", [])}
        for entry in new_entries:
            graph_data_dict[entry["guid"]] = entry
        graph_data = list(graph_data_dict.values())

        updated_metadata = {
            "user_email": request.user_email,
            "date":request.date,
            "graph_data": graph_data,
            "history": existing_json.get("history", [])
        }

        updated_metadata_df = pd.DataFrame([updated_metadata])
        blob_handler.upload_blob(updated_metadata_df, container_name, metadata_blob_name)
        logger.info("Metadata saved successfully.")

        guids = [entry["guid"] for entry in graph_data]
        queries = [entry["query"] for entry in graph_data]
        graph_suggestions = {entry["guid"]: entry.get("graph_suggestions", "") for entry in graph_data}
        table_data = [entry.get("table_data", "") for entry in graph_data]
        selected_type = {entry["guid"]: entry.get("selected_type", "") for entry in graph_data}
        selectedGraphIndices = {entry["guid"]: entry.get("selectedGraphIndices", "") for entry in graph_data}
        active_view = {entry["guid"]: entry.get("active_view", "") for entry in graph_data}
        title = [entry["title"] for entry in graph_data]
        date=updated_metadata.get("date","")

        return process_queries_in_parallel(guids, queries, graph_suggestions, table_data, active_view, selected_type, title, date,selectedGraphIndices)

    elif request.operation == "modify":
        if not existing_json:
            raise handle_api_error("No metadata found for the user.", HTTP_400_BAD_REQUEST)

        guid_to_modify = request.data.guid[0]
        new_query = request.data.query[0]
        new_suggestion = request.data.graph_suggestions.get(guid_to_modify, "")

        graph_data = existing_json.get("graph_data", [])
        updated_graph_data = []
        found = False
        for entry in graph_data:
            if entry["guid"] == guid_to_modify:
                entry["query"] = new_query
                entry["graph_suggestions"] = new_suggestion
                found = True
            updated_graph_data.append(entry)

        if not found:
            raise handle_api_error(f"No graph found with guid: {guid_to_modify}", HTTP_400_BAD_REQUEST)

        updated_metadata = {
            "user_email": request.user_email,
            "graph_data": updated_graph_data,
            "history": existing_json.get("history", [])
        }

        updated_metadata_df = pd.DataFrame([updated_metadata])
        blob_handler.upload_blob(updated_metadata_df, container_name, metadata_blob_name)
        return {"message": "Graph metadata modified successfully."}

    elif request.operation == "delete":
        if not existing_json:
            raise handle_api_error("No metadata found for the user.", HTTP_400_BAD_REQUEST)

        guid_to_delete = request.data.guid
        graph_data = [
            entry for entry in existing_json.get("graph_data", [])
            if entry["guid"] not in guid_to_delete
        ]

        updated_metadata = {
            "user_email": request.user_email,
            "graph_data": graph_data,
            "history": existing_json.get("history", [])
        }

        updated_metadata_df = pd.DataFrame([updated_metadata])
        blob_handler.upload_blob(updated_metadata_df, container_name, metadata_blob_name)
        return {"message": "Deleted successfully."}

    else:
        raise handle_api_error("Invalid operation specified.", HTTP_400_BAD_REQUEST)

@router.post("/manage_history")
def manage_history(request: HistoryPayload):
    user_id = access_control.get_user_id(request.user_email)
    container_name = history_storage_container_name
    datetime_now = str(dt.datetime.now())
    metadata_blob_name = f"metadata/{user_id}.json"

    existing_metadata = blob_handler.read_blob(container_name, metadata_blob_name)
    existing_json = extract_json(existing_metadata)

    if not existing_json:
        raise handle_api_error("No metadata found for the user.", HTTP_400_BAD_REQUEST)

    history = existing_json.get("history", [])

    if request.operation == "get_title":
        return {
            "titles": [{"title": h["title"], "blobname": h["blobname"]} for h in history]
        }

    elif request.operation == "get_data":
        if not request.history or "blobname" not in request.history[0]:
            raise handle_api_error("Missing blobname in request.", HTTP_400_BAD_REQUEST)

        blobname = request.history[0]["blobname"]
        matching_entry = next((entry for entry in history if entry["blobname"] == blobname), None)

        if not matching_entry:
            raise handle_api_error(f"No history entry found with blobname '{blobname}'.", HTTP_400_BAD_REQUEST)

        blob_data = blob_handler.read_blob(container_name, blobname, raw_json=True)

        return {
            "title": matching_entry["title"],
            "blobname": blobname,
            "message": blob_data
        }

    elif request.operation == "add":
        for entry, message in zip(request.history, request.message):
            blobname = entry.get("blobname")
            title = entry.get("title")

            if not blobname:
                unique_string = f"{user_id}_{datetime_now}_{title}"
                guid = hashlib.sha256(unique_string.encode()).hexdigest()
                blobname = f"history/{guid}.json"
                history.append({"title": title, "blobname": blobname})
            else:
                existing_entry = next((h for h in history if h["blobname"] == blobname), None)
                if not existing_entry:
                    history.append({"title": title, "blobname": blobname})

            blob_handler.upload_blob(message, container_name, blobname, raw_json=True)

    elif request.operation == "modify":
        for entry, message in zip(request.history, request.message):
            for existing_entry in history:
                if existing_entry["blobname"] == entry["blobname"]:
                    blob_handler.upload_blob(message, container_name, existing_entry["blobname"], raw_json=True)

    elif request.operation == "delete":
        blobname_to_delete = request.history[0]["blobname"]
        history = [entry for entry in history if entry["blobname"] != blobname_to_delete]

        for entry in existing_json["history"]:
            if entry["blobname"] == blobname_to_delete:
                blob_handler.delete_blob_by_user(blobname_to_delete.replace(".json", ""), container_name)

    else:
        raise handle_api_error("Invalid operation specified.", HTTP_400_BAD_REQUEST)

    updated_metadata = {
        "user_email": request.user_email,
        "graph_data": existing_json.get("graph_data", []),
        "history": history
    }

    updated_metadata_df = pd.DataFrame([updated_metadata])
    blob_handler.upload_blob(updated_metadata_df, container_name, metadata_blob_name)

    return {"message": f"History {request.operation} operation completed successfully."}



def fetch_user_logs_cost():
    query = "SELECT * FROM IntegratedAnalytics.UserLogsCost"
    return sql_helper.execute_sql_query(query, "")

def fetch_user_metrics_bu_table():
    query = "SELECT * FROM IntegratedAnalytics.UserMetricsBUTable"
    return sql_helper.execute_sql_query(query, "")

def fetch_user_metrics_datasource_table():
    query = "SELECT * FROM IntegratedAnalytics.UserMetricsDataSourceTable"
    return sql_helper.execute_sql_query(query, "")

def fetch_analytical_questions_count():
    query = "SELECT * FROM IntegratedAnalytics.AnalyticalQuestionsCount"
    return sql_helper.execute_sql_query(query, "")


@router.get("/get_user_usage_logs")
def get_user_usage_logs(current_user: Dict = Depends(require_admin_group())):
    """
    Fetches comprehensive user usage logs and metrics.
    Requires admin access.

    Args:
        current_user: Authenticated user with admin privileges.

    Returns:
        dict: User usage logs, metrics by BU, datasource, and analytical questions count.
    """
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Run all fetches in parallel
            logs_cost_future = executor.submit(fetch_user_logs_cost)
            bu_table_future = executor.submit(fetch_user_metrics_bu_table)
            datasource_table_future = executor.submit(fetch_user_metrics_datasource_table)
            analytical_questions_future = executor.submit(fetch_analytical_questions_count)

            # Get results
            user_logs_cost_df = logs_cost_future.result()
            user_metrics_bu_table_df = bu_table_future.result()
            user_metrics_datasource_table_df = datasource_table_future.result()
            analytical_questions_count_df = analytical_questions_future.result()

        return {
            "UserLogsCost": user_logs_cost_df.to_dict(orient="records"),
            "UserMetricsBUTable": user_metrics_bu_table_df.to_dict(orient="records"),
            "UserMetricsDataSourceTable": user_metrics_datasource_table_df.to_dict(orient="records"),
            "AnalyticalQuestionsCount": analytical_questions_count_df.to_dict(orient="records")
        }

    except Exception as e:
        raise handle_api_error(f"Error fetching usage logs: {e}")

def fetch_psl_forecast_data():
    query = "SELECT * FROM IntegratedAnalytics.PSLforecast"
    return sql_helper.execute_sql_query(query, "")

@router.get("/get_psl_forecast_data")
def get_psl_forecast_data():
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            forecast_future = executor.submit(fetch_psl_forecast_data)
            forecast_df = forecast_future.result()

        return {
            "PSLForecastData": forecast_df.to_dict(orient="records")
        }

    except Exception as e:
        raise handle_api_error(f"Error fetching PSL forecast data: {e}")
