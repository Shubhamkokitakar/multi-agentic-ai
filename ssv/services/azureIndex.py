import ast
from utils.logger import *
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
from azure.search.documents.models import VectorizedQuery
from config.config import cog_endpoint

class AzureSearchHelper:
    def __init__(
        self,
        service_name: str,
    ):
        self.service_name = service_name
        self.credential = DefaultAzureCredential()

    def generic_retriever(
        self,
        extracts: str,
        key: str,
        index_name: str,
        fallback_message: str,
        filters: list = None,
        fields: list = ["value", "column_name"],
    ) -> list:
        """
        Extracts a list of values from a string based on a key, then searches an Azure Cognitive Search index for matching documents.

        Args:
            extracts (str): The raw string containing the key and list of values to extract.
            key (str): The key to locate within the extracts string whose values to extract.
            index_name (str): The Azure Cognitive Search index name to query.
            fallback_message (str): Message to return if an error occurs during search.
            filters (list, optional): List of substrings to exclude from search terms (case-insensitive). Defaults to None.
            fields (list, optional): List of two field names to extract from search results, default is ["value", "column_name"].

        Returns:
            list: List of tuples or IDs from the search results matching the extracted values, 
                or a list containing the fallback_message if an error occurs.
        """
        result = []
        try:

            start = extracts.find(f"{key}:[")
            end = extracts.find("]", start)
            values = ast.literal_eval(
                extracts[(start + len(key) + 1) : extracts.find("]", start) + 1]
            )
            values = [f"'{item}'" for item in values]
        except Exception as e:
            logger.warning(f"Error loading {key}: {e}")
            return result

        if values:
            try:
                endpoint = f"https://{self.service_name}.search.windows.net"
                search_client = SearchClient(
                    endpoint=endpoint, index_name=index_name, credential=self.credential
                )

                for value in values:
                    value = value.replace("'", '"')

                    if filters and any(f in value.lower() for f in filters):
                        continue

                    results = search_client.search(
                        search_text=value, top=len(values) + 5
                    )

                    if fields == ["id"]:
                        result.extend([item["id"] for item in results])
                    else:
                        result.extend(
                            [(item[fields[0]], item[fields[1]]) for item in results]
                        )

            except Exception as e:
                logger.error(f"Error retrieving {key} with LIKE operator.\nError: {e}")
                return [fallback_message]

        return result

    def get_embedding(self, text: str) -> list:
        """
        Generates an embedding vector for the given text using Azure OpenAI embeddings API.

        Args:
            text (str): The input text to generate an embedding for.

        Returns:
            list: A list of floats representing the embedding vector.
                Returns an empty list if an error occurs.
        """
        try:
            client = AzureOpenAI(
                api_version="2023-07-01-preview",
                azure_endpoint=cog_endpoint,
                api_key=self.credential.get_token(
                    "https://cognitiveservices.azure.com/.default"
                ).token,
            )
            response = client.embeddings.create(
                input=text, model="text-embedding-ada-002-2"
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Error generating embedding for text: {e}")
            return []

    def query_retriever(self, question: str, query_reinforcement_index: str) -> list:
        """
        Retrieves related queries from an Azure Cognitive Search index based on the embedding of the input question.

        Args:
            question (str): The natural language question to embed and search for related queries.
            query_reinforcement_index (str): The name of the Azure Cognitive Search index containing reinforced queries.

        Returns:
            list or dict: 
                - A dictionary mapping 'AnalyticalQuestion' to 'QueryGenerated' for the top related queries if successful.
                - A list containing an error message if embedding generation fails or if an exception occurs.
        """
        try:
            embedding = self.get_embedding(question)
            if not embedding:
                return ["Embedding generation failed; cannot retrieve queries."]

            endpoint = f"https://{self.service_name}.search.windows.net"
            search_client = SearchClient(
                endpoint=endpoint,
                index_name=query_reinforcement_index,
                credential=self.credential,
            )

            vector_query = VectorizedQuery(
                vector=embedding,
                fields="AnalyticalQuestionEmbed",
                k_nearest_neighbors=4,
                kind="vector",
            )

            results = search_client.search(
                search_text=question,
                vector_queries=[vector_query],
                scoring_profile="hybrid_search_profile",
                top=4,
            )

            related_queries_dict = {}
            for item in results:
                related_queries_dict[item["AnalyticalQuestion"]] = item[
                    "QueryGenerated"
                ]
            return related_queries_dict

        except Exception as e:
            logger.error(f"Error retrieving related queries: {e}")
            return [
                "Error retrieving queries; please use the logic given in system prompt for querying."
            ]
