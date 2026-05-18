from fastapi import APIRouter
from pydantic import BaseModel
from config.config import *
from config.capability_metadata import capability_metadata
from utils.logger import logger
from services.blob_service import AzureBlobHandler
from services.azure_index import AzureSearchHelper
from services.access_control import AccessControl
from utils.logger import logger
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional,List

router = APIRouter()

class AIResponseFeedback(BaseModel):
    analytical_question_graph: Optional[str] = ""
    analytical_question_table: Optional[str] = ""
    graph_query: Optional[str] = ""
    table_query: Optional[str] = ""
    username: str
    ai_response_feedback: str
    detailed_feedback: Optional[str] = ""
    feedback_tags: Optional[List[str]] = []

class Feedback(BaseModel):
    feedback_rating: int
    feedback_text: str
    username: str

search_helper = AzureSearchHelper(
    service_name=service_name,
)
access_control = AccessControl(client_id, client_secret, tenant_id)
blob_handler = AzureBlobHandler(
    account_name=storage_acc_name, account_key=storage_acc_key
)

@router.post("/submit-feedback")
def submit_feedback(request: Feedback):
    """
    Submits user feedback by appending it to a blob file in Azure Storage.

    Args:
        request (Feedback): Feedback object with rating, text, and username.

    Returns:
        list: ["OK", 200] on success.
    """
    try:
        logger.info("Sending Feedback to Blob")
        feedback = request.feedback_text
        rating = request.feedback_rating
        username = request.username
        datetime = str(dt.datetime.now())

        col = ("Ratings", "Feedback", "Username", "Date")

        try:

            feedback_df = blob_handler.read_blob(
                feedback_blob_container_name, feedback_blob_name
            )
            feedback_df = feedback_df[col]

        except Exception as e:
            logger.warning(
                f"Blob Doesn't Exist or doesn't have the right structure: {e}"
            )
            feedback_df = pd.DataFrame(columns=col)

        feedback_df.loc[len(feedback_df)] = [rating, feedback, username, datetime]

        try:
            blob_handler.upload_blob(
                feedback_df, feedback_blob_container_name, feedback_blob_name
            )
        except Exception as e:
            logger.warning(f"Unable to store the data to blob due to {e}")

        return ["OK", 200]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ai-response-feedback")
def ai_response_feedback(request: AIResponseFeedback):
    """
    Submits feedback on AI-generated responses by logging it to a blob.

    Args:
        request (AIResponseFeedback): Object containing user feedback, tags, and metadata.
    """
    logger.info("Sending AI Response Feedback to Blob")
    try:
        username = request.username
        ai_response_feedback = request.ai_response_feedback
        detailed_feedback = request.detailed_feedback
        feedback_tags = request.feedback_tags
        datetime_now = str(dt.datetime.now())
        endpoint = f"https://{service_name}.search.windows.net"
        credential = DefaultAzureCredential()

        # Column schema
        col = [
            "GUID",
            "AnalyticalQuestion",
            "AnalyticalQuestionEmbed",
            "QueryGenerated",
            "Username",
            "AIResponseFeedback",
            "DetailedFeedback",
            "FeedbackTags",
            "Date",
        ]

        response_reinforcement_df = pd.DataFrame(columns=col)

        def process_question(question: Optional[str], query: Optional[str], index_name: str):
            """
            Stores AI response feedback in blob storage and, if marked 'good', uploads it to Azure Cognitive Search index.

            Args:
                question (str, optional): User's analytical question.
                query (str, optional): AI-generated SQL query.
                index_name (str): Name of the Azure Cognitive Search index.

            Returns:
                None
            """

            if question and query and len(query.strip()) > 0:
                question_embed = search_helper.get_embedding(question)
                unique_string = f"{question}_{datetime_now}"
                guid = hashlib.sha256(unique_string.encode()).hexdigest()
                guid_name = f"{guid}.json"

                response_reinforcement_df.loc[len(response_reinforcement_df)] = [
                    guid,
                    question,
                    question_embed,
                    query,
                    username,
                    ai_response_feedback,
                    detailed_feedback,
                    feedback_tags,
                    datetime_now,
                ]

                # Save to blob
                try:
                    blob_handler.upload_blob(
                        response_reinforcement_df.tail(1),  # Upload the latest row
                        ai_response_feedback_container_name,
                        guid_name,
                    )
                    logger.info(f"Uploaded feedback to blob: {guid_name}")
                except Exception as e:
                    logger.warning(f"Unable to store feedback in blob due to: {e}")

                # Upload to vector index if feedback is good
                if ai_response_feedback == "good":
                    try:
                        response_reinforcement_df_filt = response_reinforcement_df.tail(1)[
                            [
                                "GUID",
                                "AnalyticalQuestion",
                                "AnalyticalQuestionEmbed",
                                "QueryGenerated",
                                "Username",
                                "Date",
                            ]
                        ]
                        search_client = SearchClient(
                            endpoint=endpoint,
                            index_name=index_name,
                            credential=credential,
                        )
                        documents = response_reinforcement_df_filt.to_dict(orient="records")
                        search_client.upload_documents(documents=documents)
                        logger.info(f"Successfully uploaded feedback to index {index_name}")
                    except Exception as e:
                        logger.warning(f"Ingestion to vector index {index_name} failed: {e}")
        logger.info(f"{html.escape(str(request.analytical_question_graph))},{html.escape(str(request.graph_query))}")
        logger.info(f"{html.escape(str(request.analytical_question_table))},{html.escape(str(request.table_query))}")
        process_question(
            request.analytical_question_graph,
            request.graph_query,
            query_reinforcement_graph_index,
        )

        # Process table question
        process_question(
            request.analytical_question_table,
            request.table_query,
            query_reinforcement_table_index,
        )

        return ["OK", 200]

    except Exception as e:
        logger.warning(f"Response Reinforcement logs Failed to Update: {e}")
        raise HTTPException(status_code=500, detail=str(e))
