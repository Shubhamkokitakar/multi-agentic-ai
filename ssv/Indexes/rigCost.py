# Databricks notebook source
# DBTITLE 1,Import the libraries
import requests, json, ast, hashlib
import os


from azure.search.documents import SearchClient

from azure.core.credentials import AzureKeyCredential
import detk 
from pyspark.sql.functions import col, lit
import warnings
import pandas as pd
tk=detk.Detk(secret_location = 'dbsecrets')
cols_to_index = ["Rigs"]
warnings.filterwarnings("ignore")

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
dbutils.widgets.multiselect(
    "indexName", "All", ["All"] + cols_to_index, "Select Indexes to Update"
)

# COMMAND ----------

# DBTITLE 1,Variables
cvx_environment = dbutils.widgets.get("environment")
subscription_mnemonic = "p118" if cvx_environment == "prod" else "t118"
cog_search_env = "test" if "t" in subscription_mnemonic else "prod"
dls_env = "" if cvx_environment == "prod" else cvx_environment

# COMMAND ----------

# DBTITLE 1,Index Configuration
delete_index_flag = True if dbutils.widgets.get("deleteIndex") == "True" else False
create_index_flag = True if dbutils.widgets.get("createIndex") == "True" else False
indexes_to_update = dbutils.widgets.get("indexName").split(",")

indexes_to_update = cols_to_index if "All" in indexes_to_update else indexes_to_update

# Replace with your Azure Cognitive Search service name and admin key
service_name = f"pf-{subscription_mnemonic}-cog-srch-{cog_search_env}-ussc-cvx"
api_key = dbutils.secrets.get("dbsecrets", "azure-cogservice-api-key")

getIndexName = lambda col: f"az-cogsearch-ssvia-{col}-{cvx_environment}".lower()

# Create a SearchIndexClient
endpoint = f"https://{service_name}.search.windows.net"
credential = AzureKeyCredential(api_key)

# COMMAND ----------

# DBTITLE 1,Import the data
dls=tk.Data.connect_datalake(datalake_name=f"chevrondatalake{dls_env}")
adls_path = dls.get_container_path(container= "produced")
RigCost = dls.spark_session.read.parquet(f"{adls_path}PSCM/SSV/RigCost")

# COMMAND ----------

# DBTITLE 1,Function to delete index

def delete_index(index, endpoint=endpoint, api_key=api_key):

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

# DBTITLE 1,Delete Index
if delete_index_flag:
    for index_col in indexes_to_update:
        delete_index(getIndexName(index_col))

# COMMAND ----------

# DBTITLE 1,Function to create new index

def create_cogsearch_index(column, endpoint=endpoint, api_key=api_key):

    index_name = getIndexName(column)

    endpoint = f"{endpoint}/indexes/{index_name}?api-version=2024-07-01&allowIndexDowntime=true"
    print(endpoint)
    # Define the headers
    headers = {"Content-Type": "application/json", "api-key": api_key}

    # Define the index schema and vector search configuration
    index_definition = {
        "name": index_name,
        "fields": [
            {
                "name": "id",
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
                "name": "value",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "stored": True,
                "key": False,
            },
            {
                "name": "column_name",
                "type": "Edm.String",
                "searchable": True,
                "retrievable": True,
                "stored": True,
                "key": False,
            },
        ],
        "similarity": {
            "@odata.type": "#Microsoft.Azure.Search.BM25Similarity",
            "b": 0.1,  # ( 0 - 1 ) Penalize longer documents (we don't need to penalize longer docs)
            "k1": 2.7,  # ( 0 - 3 ) Higher score would prioritize presence of all words over single word multiple times
        },
    }

    # Make the request to create the index
    response = requests.put(
        endpoint, headers=headers, data=json.dumps(index_definition)
    )

    # Check the response
    if response.status_code == 201:
        print("Index created successfully.")
    else:
        print(f"Error: {response.status_code}, {response.text}")

    return response.status_code


# COMMAND ----------

# DBTITLE 1,Creating Index
if create_index_flag:
    for index_col in indexes_to_update:
        create_cogsearch_index(index_col)

# COMMAND ----------


def upload_data_to_cog_search(
    RigCost,
    column,
    start_index=0,
    window=10000,
    credential=credential,
    endpoint=endpoint,
):

    index_name = getIndexName(column)
    search_client = SearchClient(
        endpoint=endpoint, index_name=index_name, credential=credential
    )
    columns = list()
    if column == "Rigs":
        columns = ["RigName"]

    for column_ in columns:
        RigCost = (
            RigCost.withColumn("column_name", lit(column_))
            .select(
                col(column_).alias("value"),
                col(f"{column_}GUID").alias("id"),
                "column_name",
            )
            .dropDuplicates(["value"])
        )

        df = RigCost.filter(
            (col("value") != "None")
            & (col("value").isNotNull())
            & (col("value") != "null")
        ).na.drop(subset=["value"])
        total_size = df.count()
        print(f"Total size of the data: {total_size}")
        # Create an index column
        df = df.rdd.zipWithIndex().toDF(["id", "index"]).select("id.*", "index")
        # df = df.filter(col(column) != "null").na.drop("any")
        print("uploading started")
        start_index = 0
        # # Loop to process DataFrame in chunks
        for start in range(0, total_size, window):
            print(
                f"Processing records from {start_index} to {start_index + window - 1}",
                end="\r",
            )
            filtered_df = df.filter(
                (col("index") >= start_index) & (col("index") < (start_index + window))
            ).drop("index")
            filtered_df = filtered_df.toPandas()
            jsonified_df = filtered_df.to_json(orient="records")

            if type(jsonified_df) == str:
                documents = ast.literal_eval(jsonified_df)
            result = search_client.upload_documents(documents=documents)
            start_index += window

        print("\nupload complete")


# COMMAND ----------

# DBTITLE 1,Upload embeds
for index_col in indexes_to_update:
    print(f"Updating Index for {index_col}")
    upload_data_to_cog_search(RigCost, index_col, window=32000)
