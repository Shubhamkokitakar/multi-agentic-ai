from azure.storage.blob import BlobServiceClient
from io import BytesIO, StringIO
import pandas as pd
import json
from utils.logger import logger
from config.config import *
class AzureBlobHandler:
    def __init__(self, account_name: str, account_key: str):
        """
        Initializes the Azure Blob Storage client with the provided account credentials.

        Args:
            account_name (str): The Azure storage account name.
            account_key (str): The Azure storage account key.

        Raises:
            ValueError: If either account_name or account_key is missing or empty.
        """
        if not account_name or not account_key:
            logger.error("Azure storage account credentials are missing.")
            raise ValueError("Missing Azure storage credentials.")

        self.account_name = account_name
        self.account_key = account_key
        self.service_client = BlobServiceClient(
            f"https://{account_name}.blob.core.windows.net/", credential=account_key
        )

    def get_container_client(self, container_name: str):
        """
        Retrieves a Blob Container client for the specified container name.

        Args:
            container_name (str): The name of the Azure Blob Storage container.

        Returns:
            ContainerClient: An instance of ContainerClient for interacting with the specified container.
        """
        return self.service_client.get_container_client(container_name)

    def read_blob(self, container_name: str, blob_name: str = None, raw_json: bool = False):
        """
        Reads a specific blob if provided, or returns all blobs in the container.
        """
        try:
            container_client = self.get_container_client(container_name)

            if not container_client.exists():
                logger.warning(f"Container '{container_name}' does not exist.")
                return {}

            if blob_name:
                return self._read_single_blob(container_client, blob_name,raw_json)

            return self._read_all_blobs(container_client)

        except Exception as e:
            logger.error(f"Failed to process blob data: {e}")
            return pd.DataFrame(columns=["Ratings", "Feedback"]) if blob_name else {}

    def _read_single_blob(self, container_client, blob_name, raw_json: bool = False):
        """
        Reads a blob and returns its content as a DataFrame or raw JSON.

        Args:
            container_client (ContainerClient): Azure Blob container client.
            blob_name (str): Name of the blob to read.
            raw_json (bool): If True, return raw JSON string instead of DataFrame.

        Returns:
            Union[pd.DataFrame, str]: DataFrame with blob data or raw JSON string.
        """
        blob_client = container_client.get_blob_client(blob_name)

        if not blob_client.exists():
            logger.warning(f"Blob '{html.escape(str(blob_name))}' not found.")
            return pd.DataFrame(columns=["Ratings", "Feedback"])
        blob_data = blob_client.download_blob().readall()
        extn = blob_name.split(".")[-1].lower()

        if raw_json:
            return blob_data.decode("utf-8")  # Return as string for json.loads()

        try:
            if extn == "json":
                df = pd.read_json(BytesIO(blob_data))
            elif extn == "parquet":
                df = pd.read_parquet(BytesIO(blob_data))
            elif extn == "csv":
                df = pd.read_csv(StringIO(blob_data.decode("utf-8")))
            else:
                logger.warning(f"Unsupported file format: {html.escape(str(blob_name))}")
                return pd.DataFrame(columns=["Ratings", "Feedback"])

            df.insert(0, "slNo", range(1, len(df) + 1))
            return df

        except Exception as e:
            logger.error(f"Failed to parse blob '{html.escape(str(blob_name))}': {html.escape(str(e))}")
            return pd.DataFrame(columns=["Ratings", "Feedback"])

    def _read_all_blobs(self, container_client):
        """
        Reads all blobs in the container, returning their data as dicts.

        Args:
            container_client (ContainerClient): Azure Blob container client.

        Returns:
            dict: Keys are blob names; values are lists of records with added 'slNo' indices.
                Skips unsupported formats.
        """
        all_blob_data = {}
        serial_no = 0

        for blob in container_client.list_blobs():
            blob_name = blob.name
            blob_client = container_client.get_blob_client(blob_name)
            blob_data = blob_client.download_blob().readall()
            extn = blob_name.split(".")[-1].lower()

            if extn == "json":
                data = json.loads(blob_data.decode("utf-8"))
                for item in data:
                    item["slNo"] = serial_no
                    serial_no += 1
                all_blob_data[blob_name] = data

            elif extn in ["parquet", "csv"]:
                if extn == "parquet":
                    df = pd.read_parquet(BytesIO(blob_data))
                else:
                    df = pd.read_csv(StringIO(blob_data.decode("utf-8")))

                df.insert(0, "slNo", range(serial_no, serial_no + len(df)))
                serial_no += len(df)
                all_blob_data[blob_name] = df.to_dict(orient="records")
            else:
                logger.warning(f"Skipping unsupported file format: {blob_name}")

        return all_blob_data

    def upload_blob(self, data, container_name: str, blob_name: str, raw_json: bool = False):
        """
        Uploads data to a blob in CSV, Parquet, or JSON format.

        Args:
            data (Union[pd.DataFrame, List[dict]]): Data to upload.
            container_name (str): Target container name.
            blob_name (str): Blob name including extension (.csv, .parquet, .json).
            raw_json (bool): If True, treat `data` as a list of dicts and serialize directly.

        Raises:
            ValueError: If the file format is unsupported.
        """
        try:
            extn = blob_name.split(".")[-1].lower()

            if extn == "csv" and isinstance(data, pd.DataFrame):
                output = StringIO()
                data.to_csv(output, index=False)
                final_output = output.getvalue()
            elif extn == "parquet" and isinstance(data, pd.DataFrame):
                output = BytesIO()
                data.to_parquet(output)
                final_output = output.getvalue()
            elif extn == "json":
                if raw_json:
                    final_output = json.dumps(data, indent=2)
                elif isinstance(data, pd.DataFrame):
                    final_output = data.to_json(orient="records")
                else:
                    raise ValueError("Unsupported data type for JSON upload.")
            else:
                raise ValueError("Unsupported file format for upload.")

            container_client = self.get_container_client(container_name)

            if not container_client.exists():
                logger.info("Container does not exist. Creating one.")
                container_client.create_container()

            blob_client = container_client.get_blob_client(blob_name)
            
        # Delete existing blob and its snapshots before uploading
            try:
                blob_client.delete_blob(delete_snapshots="include")
                logger.info(f"Deleted existing blob and snapshots: {blob_name}")
            except Exception as delete_error:
                logger.warning(f"No existing blob or snapshots to delete: {delete_error}")

            blob_client.upload_blob(final_output, overwrite=True)

        except Exception as e:
            logger.error(f"Failed to upload blob: {e}")

    def delete_blob_by_user(self, user_id: str, container_name: str):
        """
        Deletes the blob named '{user_id}.json' in the specified container.

        Args:
            user_id (str): User identifier used as blob name prefix.
            container_name (str): Azure Blob container name.

        Returns:
            str: Success or error message.
        """
        try:
            blob_name = f"{user_id}.json"
            container_client = self.get_container_client(container_name)

            if not container_client.exists():
                return f"Container {container_name} does not exist."

            blob_client = container_client.get_blob_client(blob_name)

            if blob_client.exists():
                blob_client.delete_blob()
                return f"Blob {blob_name} removed successfully."
            else:
                return f"Blob {blob_name} not found."
        except Exception as e:
            logger.error(f"Error deleting blob: {e}")
            return f"Failed to delete blob {user_id}.json"
