# Databricks notebook source
# DBTITLE 1,Import the libraries
import os
import warnings
import pandas as pd
import requests, json, ast
from pyspark.sql.functions import sha2
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

warnings.filterwarnings("ignore")

# COMMAND ----------

with open("SampleDefaultQueries-Graph.json", "r") as file:
    file_content = file.read()
sample_default_docs=ast.literal_eval(file_content)

# COMMAND ----------

# DBTITLE 1,Overall Configuration
os.environ.update(
    {
        "AZURE_CLIENT_ID": dbutils.secrets.get("dbsecrets", "client-id"),
        "AZURE_TENANT_ID": dbutils.secrets.get("dbsecrets", "tenant-id"),
        "AZURE_CLIENT_SECRET": dbutils.secrets.get("dbsecrets", "app-secret"),
    }
)

# COMMAND ----------

# DBTITLE 1,Widget for environment
dbutils.widgets.dropdown("environment", "dev", ["dev", "test", "prod"])
dbutils.widgets.dropdown("deleteIndex", "False", ["True", "False"])
dbutils.widgets.dropdown("createIndex", "False", ["True", "False"])
dbutils.widgets.dropdown("restoreFromBlobIndex", "False", ["True", "False"])

# COMMAND ----------

# DBTITLE 1,Variables
cvx_environment = dbutils.widgets.get("environment")
subscription_mnemonic = "p118" if cvx_environment == "prod" else "t118"
cog_search_env = "test" if "t" in subscription_mnemonic else "prod"
dls_env = "" if cvx_environment == "prod" else cvx_environment
storage_acc_name = f"ssv{subscription_mnemonic}cvx"
storage_acc_key = dbutils.secrets.get(
    "dbsecrets", f"connectionstring-{storage_acc_name}-key2"
)

# COMMAND ----------

# DBTITLE 1,Index Configuration
delete_index_flag = True if dbutils.widgets.get("deleteIndex") == "True" else False
create_index_flag = True if dbutils.widgets.get("createIndex") == "True" else False
restore_from_blob_index_flag = (
    True if dbutils.widgets.get("restoreFromBlobIndex") == "True" else False
)

# Replace with your Azure Cognitive Search service name and admin key
service_name = f"pf-{subscription_mnemonic}-cog-srch-{cog_search_env}-ussc-cvx"
api_key = dbutils.secrets.get("dbsecrets", "azure-cogservice-api-key")

indexName = "query-reinforcement"
getIndexName = lambda col: f"az-cogsearch-ssvia-{col}-{cvx_environment}".lower()

container = "ssvdev-airesponse-feedback"

# Create a SearchIndexClient
endpoint = f"https://{service_name}.search.windows.net"
credential = AzureKeyCredential(api_key)

# COMMAND ----------

# DBTITLE 1,Function to delete index

def delete_index(indexName, endpoint=endpoint, api_key=api_key):

    index = getIndexName(indexName)

    # Define the endpoint
    endpoint = f"{endpoint}/indexes/{index}?api-version=2024-07-01"

    # Define the headers
    headers = {"Content-Type": "application/json", "api-key": api_key}

    # Make the request to delete the index
    response = requests.delete(endpoint, headers=headers)

    # Check the response
    if response.status_code == 204:
        print("Index deleted successfully.")
    else:
        print(f"Error: {response.status_code}, {response.text}")

    return response.status_code


# COMMAND ----------

# DBTITLE 1,Deleting Index If delete index flag is true
if delete_index_flag:
    delete_index(indexName)


# COMMAND ----------

# DBTITLE 1,Uploading Documents to Search Index in Batches

def upload_documents(response_reinforcement, indexName):
    index_name = getIndexName(indexName)
    search_client = SearchClient(
        endpoint=endpoint, index_name=index_name, credential=credential
    )
    if isinstance(response_reinforcement, str):
        documents = ast.literal_eval(response_reinforcement)
    else:
        documents = response_reinforcement
    total_docs = len(documents)
    print(f"uploading {total_docs} documents to index.")
    for index in range(0, total_docs, 3000):
        documents_to_upload = documents[index : index + 3000]
        search_client.upload_documents(documents=documents_to_upload)
        print(f"uploaded {index+3000} documents to index.")
    print("uploaded restored blob documents to index.")


# COMMAND ----------

# DBTITLE 1,Creating a Custom Search Index and uploading default values
def create_cogsearch_index(indexName, endpoint=endpoint, api_key=api_key, restore_from_blob_index_flag=True):
    index_name = getIndexName(indexName)

    endpoint = f"{endpoint}/indexes/{index_name}?api-version=2024-07-01&allowIndexDowntime=true"
    print(endpoint)
    # Define the headers
    headers = {"Content-Type": "application/json", "api-key": api_key}

    # Define the index schema and vector search configuration
    index_definition = {
        "name": index_name,
        "fields": [
            {
                "name": "GUID",
                "type": "Edm.String",
                "searchable": True,
                "filterable": True,
                "retrievable": True,
                "stored": True,
                "sortable": True,
                "facetable": True,
                "key": True,
            },
            {
                "name": "AnalyticalQuestion",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "stored": True,
                "key": False,
            },
            {
                "name": "AnalyticalQuestionEmbed",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": True,
                "stored": True,
                "key": False,
                "dimensions": 1536,
                "vectorSearchProfile": "cosine_similarity_profile",
            },
            {
                "name": "QueryGenerated",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "stored": True,
                "key": False,
            },
            {
                "name": "Username",
                "type": "Edm.String",
                "retrievable": True,
                "stored": True,
                "key": False,
            },
            {
                "name": "Date",
                "type": "Edm.String",
                "retrievable": True,
                "stored": True,
                "key": False,
            },
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "cosine_similarity",
                    "kind": "exhaustiveKnn",
                    "exhaustiveKnnParameters": {"metric": "cosine"},
                }
            ],
            "profiles": [
                {"name": "cosine_similarity_profile", "algorithm": "cosine_similarity"}
            ],
        },
        "similarity": {
            "@odata.type": "#Microsoft.Azure.Search.BM25Similarity",
            "b": 0.7,  # ( 0 - 1 ) Penalize longer documents (we don't need to penalize longer docs)
            "k1": 1.5,  # ( 0 - 3 ) Higher score would prioritize presence of all words over single word multiple times
        },
        "scoringProfiles": [
            {
                "name": "hybrid_search_profile",
                "text": {
                    "weights": {
                        "AnalyticalQuestion": 2.0  # Boost the relevance of text matches in this field
                    }
                }
            }
        ]
    }

    # Make the request to create the index
    response = requests.put(endpoint, headers=headers, data=json.dumps(index_definition))

    # Check the response
    if response.status_code == 201:
        print("Index created successfully.")
        upload_documents(sample_default_docs, indexName)
    else:
        print(f"Error: {response.status_code}, {response.text}")
    return response.status_code

# COMMAND ----------

# DBTITLE 1,Creating Index
if create_index_flag:
    create_cogsearch_index(indexName)

# COMMAND ----------

# DBTITLE 1,Restore good responses from blob

def get_all_doc_from_blob(container):
    blob_service_client = BlobServiceClient(
        f"https://{storage_acc_name}.blob.core.windows.net/", storage_acc_key
    )

    # Specify the container and blob (file) you want to delete
    blob_name = "*"
    container_client = blob_service_client.get_container_client(container)

    # Step 3: List and download all blobs
    blob_list = container_client.list_blobs()
    data_list = []
    for blob in blob_list:
        blob_client = container_client.get_blob_client(blob.name)
        data = blob_client.download_blob().readall()
        data_list.append(json.loads(data))
    flattened_list = [
        {
            key: item[key]
            for key in [
                "GUID",
                "AnalyticalQuestion",
                "AnalyticalQuestionEmbed",
                "QueryGenerated",
                "Username",
                "Date",
            ]
            if key in item
        }
        for sublist in data_list
        for item in sublist
        if item.get("AIResponseFeedback") == "good"
    ]
    return flattened_list


# COMMAND ----------

if restore_from_blob_index_flag:
    sample_default_docs = get_all_doc_from_blob(container)
    upload_documents(sample_default_docs, indexName)
