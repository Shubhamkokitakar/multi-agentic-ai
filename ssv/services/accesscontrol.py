import re
from azure.identity import ClientSecretCredential
from msgraph.core import GraphClient
import requests
from config.config import *
from urllib.parse import urlencode


class AccessControl:
    def __init__(self, client_id, client_secret, tenant_id):
        """
        Initializes the authentication client with Azure credentials.

        Args:
            client_id (str): The client/application ID for Azure AD authentication.
            client_secret (str): The client secret associated with the Azure AD application.
            tenant_id (str): The Azure AD tenant ID.

        Attributes:
            client (Any): The authenticated client object returned by the authenticate method.
            access_token (str): The access token obtained for making authorized API requests.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.client = self.authenticate()
        self.access_token = self.get_access_token()

    def authenticate(self):
        """
        Authenticates the client using Azure AD credentials and initializes the Graph client.

        Returns:
            GraphClient or None: An authenticated GraphClient instance if successful; 
            otherwise, None.
        """
        try:
            credential = ClientSecretCredential(
                self.tenant_id, self.client_id, self.client_secret
            )
            client = GraphClient(credential=credential)
            return client
        except Exception as e:
            logger.info(f"Authentication failed: {e}")
            return None

    def get_access_token(self):
        """
        Retrieves an access token from Azure AD using client credentials flow.

        Returns:
            str or None: The access token if the request is successful; otherwise, None.
        """
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, data=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            logger.info(f"Error: {response.status_code}, {response.text}")
            return None

    def add_user_to_group(self, group_id, user_id):
        """
        Adds a user to an Azure AD group using Microsoft Graph API.

        Args:
            group_id (str): The ID of the Azure AD group.
            user_id (str): The ID of the user to be added to the group.

        Returns:
            bool: True if the user was added successfully; False otherwise.
        """
        try:
            response = self.client.post(
                f"/groups/{group_id}/members/$ref",
                json={"@odata.id": f"https://graph.microsoft.com/v1.0/users/{user_id}"},
            )
            if response.status_code == 204:
                logger.info("User added successfully.")
            else:
                logger.info(f"Failed to add user: {response.json()}")
        except Exception as e:
            logger.info(f"Error adding user to group: {e}")

    def remove_user_from_group(self, group_id, user_id):
        """
        Removes a user from an Azure AD group using Microsoft Graph API.

        Args:
            group_id (str): The ID of the Azure AD group.
            user_id (str): The ID of the user to be removed from the group.

        Returns:
            bool: True if the user was removed successfully; False otherwise.
        """
        try:
            response = self.client.delete(f"/groups/{group_id}/members/{user_id}/$ref")
            if response.status_code == 204:
                logger.info("User removed successfully.")
            else:
                logger.info(f"Failed to remove user: {response.json()}")
        except Exception as e:
            logger.info(f"Error removing user from group: {e}")

    def get_user_id(self, email):
        """
        Retrieves the Azure AD user ID for a given email address using Microsoft Graph API.

        Args:
            email (str): The email address (userPrincipalName) of the user.

        Returns:
            str or None: The user's Azure AD object ID if found; otherwise, None.
        """
        try:
            response = self.client.get(
                "/users", params={"$filter": f"userPrincipalName eq '{email}'"}
            )
            if response.status_code == 200:
                users = response.json().get("value", [])
                if users:
                    return users[0]["id"]
                else:
                    logger.info(f"User with email '{email}' not found.")
                    return None
            else:
                logger.info(
                    f"Error fetching user: {response.status_code} - {response.json()}"
                )
                return None
        except Exception as e:
            logger.info(f"Error fetching user ID: {e}")
            return None

    def get_group_members(self, group_dict_list):
        """
        Retrieves members of multiple Azure AD groups using Microsoft Graph API.

        Args:
            group_dict_list (list): A list of dictionaries containing group details.
                Each dictionary should have the keys:
                    - "group_id" (str): The Azure AD group ID.
                    - "group_name" (str, optional): The name of the group.

        Returns:
            list: A list of dictionaries with user details including display name, 
                job title, email, phone numbers, office location, and group persona.
        """
        all_users = []
        serial_no = 0
        for group in group_dict_list:
            group_id = group.get("group_id")
            group_name = group.get("group_name", "Unknown Group").replace(
                "Supplier Spend Visibility - ", ""
            )
            try:
                response = self.client.get(f"/groups/{group_id}/members")
                if response.status_code == 200:
                    members = response.json().get("value", [])
                    for member in members:
                        all_users.append(
                            {
                                "slNo": serial_no,
                                "username": member.get("displayName"),
                                "jobTitle": member.get("jobTitle"),
                                "email": member.get("mail"),
                                "businessPhones": member.get("businessPhones"),
                                "officeLocation": member.get("officeLocation"),
                                "persona": group_name,
                            }
                        )
                        serial_no += 1
                else:
                    logger.info(
                        f"Failed to get members for group {group_name}: {response.json()}"
                    )
            except Exception as e:
                logger.info(f"Error retrieving members for group {group_name}: {e}")
        return all_users

    
    def search_azure_users(self, query, save_flag=False):
        """
        Searches Azure AD users by email or display name using Microsoft Graph API.

        Args:
            query (str): The search query string. Can be a full email or partial display name.
            save_flag (bool, optional): If True, includes additional user details 
                                        such as job title, office location, and phone numbers. 
                                        Defaults to False.

        Returns:
            list or str: A list of matched user dictionaries if found; otherwise, 
                        a message string indicating no matches or an error.
        """
        if not self.access_token:
            return "Error: No Access Token Available"

        if not re.match(r"^[\w\s@.-]{1,100}$", query):
            return "Error: Invalid search query"

        base_fields = "displayName,mail"
        additional_fields = ",jobTitle,officeLocation,businessPhones" if save_flag else ""
        fields = base_fields + additional_fields

        if "@" in query:
            params = {"$filter": f"mail eq '{query}'", "$select": fields}
        else:
            params = {"$search": f'"displayName:{query}"', "$select": fields}

        url = "https://graph.microsoft.com/v1.0/users?" + urlencode(params)

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "ConsistencyLevel": "eventual",
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            users = response.json().get("value", [])

            if not users:
                return f"No users found matching '{query}'."

            return [
                {
                    "username": user.get("displayName", "") or "",
                    "email": user.get("mail", "") or "",
                    **(
                        {
                            "jobTitle": user.get("jobTitle", "") or "",
                            "officeLocation": user.get("officeLocation", "") or "",
                            "businessPhones": (
                                user.get("businessPhones", [""])[0]
                                if isinstance(user.get("businessPhones"), list)
                                and user["businessPhones"]
                                else ""
                            ),
                        }
                        if save_flag
                        else {}
                    ),
                }
                for user in users
            ]
        except requests.exceptions.RequestException as e:
            return f"Error: {str(e)}"

    def is_email_in_groups(self, email, group_ids, check_membership=True):
        """
        Checks if a user identified by email is a member of any given Azure AD groups.

        Args:
            email (str): The user's email address (userPrincipalName).
            group_ids (list): List of Azure AD group IDs to check membership against.
            check_membership (bool, optional): 
                If True (default), returns True/False indicating membership.
                If False, returns a list of groups the user belongs to (empty if none).

        Returns:
            bool or list: 
                - If check_membership is True, returns True if user is member of any group; otherwise False.
                - If check_membership is False, returns list of group IDs the user belongs to (empty if none).
        """
        try:
            user_response = self.client.get(f"/users/{email}")
            if user_response.status_code != 200:
                logger.info(f"Failed to get user: {user_response.json()}")
                return False if check_membership else []

            user_id = user_response.json().get("id")
            if not user_id:
                logger.info("User ID not found.")
                return False if check_membership else []

            for group_id in group_ids:
                group_response = self.client.get(
                    f"/groups/{group_id}/members/{user_id}/$ref"
                )
                if group_response.status_code == 200:
                    logger.info(f"User {email} is a member of group {group_id}.")
                    return True

            logger.info(f"User {email} is not a member of any of the specified groups.")
            return False
        except Exception as e:
            logger.info(f"Error checking email in groups: {e}")
            return False if check_membership else []
