from fastapi import APIRouter, Depends, HTTPException
from utils.logger import logger
from config.config import *
from services.blob_service import AzureBlobHandler
from services.azure_index import AzureSearchHelper
from services.access_control import AccessControl
from pydantic import BaseModel
from typing import List, Dict
from security.authentication_middleware import require_admin_group

logger.info("Access control module initialized.")

router = APIRouter()

class GetAllMembers(BaseModel):
    group_dict: List[Dict[str, str]]


class AccessControls(BaseModel):
    user_email: str
    group_id: str
    previous_group_id: str
    operational_flag: str


class GetUserEmail(BaseModel):
    typed_text: str


class StoreAccessRequest(BaseModel):
    user_email: str
    persona: str


search_helper = AzureSearchHelper(
    service_name=service_name,
)
access_control = AccessControl(client_id, client_secret, tenant_id)
blob_handler = AzureBlobHandler(
    account_name=storage_acc_name, account_key=storage_acc_key
)


@router.post("/get-all-members")
def get_all_members(
    request: GetAllMembers,
    current_user: Dict = Depends(require_admin_group())
):
    """
    Fetches all members from specified groups.
    Requires admin access.

    Args:
        request (GetAllMembers): Request object containing group information.
        current_user: Authenticated user with admin privileges.

    Returns:
        list: List of group members.
    """
    members_list = access_control.get_group_members(request.group_dict)
    return members_list


@router.get("/get-access-requests")
def get_access_request(current_user: Dict = Depends(require_admin_group())):
    """
    Fetches all access requests from blob storage.
    Requires admin access.

    Args:
        current_user: Authenticated user with admin privileges.

    Returns:
        list: Flattened list of access request records.
    """
    requests = blob_handler.read_blob(access_request_blob_container_name)
    requests = [item for sublist in requests.values() for item in sublist]
    return requests


@router.post("/store-access-request")
def store_access_request(request: StoreAccessRequest):
    """
    Stores an access request for a user in blob storage.

    Args:
        request (StoreAccessRequest): Request object containing user_email and persona.

    Returns:
        str: Success message or error details.
    """
    try:
        user_email = request.user_email
        persona = request.persona

        if not user_email:
            raise HTTPException(status_code=400, detail="Missing user email")
        user_id = access_control.get_user_id(user_email)
        result = access_control.search_azure_users(user_email, save_flag=True)
        if not result or not isinstance(result, list):
            raise HTTPException(
                status_code=404, detail=f"No user details found for {user_email}"
            )

        user = result[0] or {}
        username = user.get("username", "")
        jobTitle = user.get("jobTitle", "")
        officeLocation = user.get("officeLocation", "")
        businessPhones = user.get("businessPhones", "")

        guid_name = f"{user_id}.json"

        col = [
            "username",
            "jobTitle",
            "email",
            "businessPhones",
            "officeLocation",
            "persona",
        ]
        access_request_df = pd.DataFrame(columns=col)

        access_request_df.loc[len(access_request_df)] = [
            username,
            jobTitle,
            user_email,
            businessPhones,
            officeLocation,
            persona,
        ]

        blob_handler.upload_blob(
            access_request_df, access_request_blob_container_name, guid_name
        )
        return "access request Updated successfully"

    except HTTPException:
        raise
    except Exception:
        logger.error("store_access_request failed", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again later.")

@router.post("/get-user-email")
def get_user_email(request: GetUserEmail):
    """
    Fetches user emails matching the typed text from Azure AD.

    Args:
        request (GetUserEmail): Request containing the typed text for search.

    Returns:
        list or dict: List of matching user emails or a message if none found.
    """
    try:
        related_emails = access_control.search_azure_users(request.typed_text.strip())
        if not related_emails:
            return []
        return related_emails
    except Exception:
        # SECURITY: Log full stack trace server-side only, never expose to client
        logger.error("get_user_email failed", exc_info=True)
        # Return generic error without any exception details
        raise HTTPException(
            status_code=500, 
            detail="An internal error occurred. Please try again later."
        )



@router.post("/access-control")
def handle_access_control(
    request: AccessControls,
    current_user: Dict = Depends(require_admin_group())
):
    """
    Process user group access operations: move, remove, add, accept, reject.
    Requires admin access.

    Args:
        request (AccessControls): Operation details.
        current_user: Authenticated user with admin privileges.

    Returns:
        dict: Success message.

    Raises:
        HTTPException: On invalid input.
    """
    if request.operational_flag not in {"move", "remove", "add", "accept", "reject"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid operational_flag. Select from: move, remove, add, accept, reject",
        )
    try:
        user_id = (
            access_control.get_user_id(request.user_email)
            if request.user_email
            else None
        )
        if not user_id:
            raise ValueError("Invalid email provided")
    except Exception:
        raise HTTPException(status_code=400, detail="Please provide a valid email")

    if request.operational_flag == "move":
        if request.previous_group_id:
            access_control.remove_user_from_group(request.previous_group_id, user_id)
        access_control.add_user_to_group(request.group_id, user_id)
    elif request.operational_flag == "remove":
        access_control.remove_user_from_group(request.group_id, user_id)
    elif request.operational_flag == "add":
        if not access_control.is_email_in_groups(request.user_email, request.group_id):
            access_control.add_user_to_group(request.group_id, user_id)
    elif request.operational_flag == "accept":
        if not access_control.is_email_in_groups(request.user_email, request.group_id):
            access_control.add_user_to_group(request.group_id, user_id)
            blob_handler.delete_blob_by_user(
                user_id, access_request_blob_container_name
            )
    elif request.operational_flag == "reject":
        blob_handler.delete_blob_by_user(user_id, access_request_blob_container_name)

    return {"message": "Operation completed successfully"}