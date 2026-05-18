import concurrent.futures
from utils.logger import *
from config.config import *
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
)
from services.azure_index import AzureSearchHelper

class Agent(AzureSearchHelper):
    def __init__(self, llm):
        """
        Initializes the EntityAgent with an LLM instance.

        Args:
            llm (object): The language model used for all agents.
        """
        self.llm = llm
        super().__init__(service_name=service_name)

    def run_agent_chain(
        self,
        question: str,
        agent_definition: str,
        system_inputs: dict = None,
        human_inputs: dict = None,
        post_process: callable = None,
    ):
        """
        Runs a generic LLM agent using system and human prompt templates.

        Args:
            question (str): The user's input.
            agent_definition (str): System prompt template.
            system_inputs (dict): Optional system context.
            human_inputs (dict): Optional dynamic variables for human template.
            post_process (callable): Optional function to clean/process the output.

        Returns:
            tuple: (Agent output content, output token count, input token count)
        """
        human_prompt = question if not human_inputs else question.format(**human_inputs)

        prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate(input_variables=[], template=agent_definition)
                ),
                HumanMessagePromptTemplate(
                    prompt=PromptTemplate(input_variables=[], template="{human_prompt}")
                ),
            ]
        )

        chain = prompt | self.llm

        input_dict = {}
        if system_inputs:
            input_dict.update(system_inputs)

        input_dict.update(
            {
                "question": question,
                "human_prompt": human_prompt,
            }
        )

        result = chain.invoke(input_dict)
        content = result.content.replace("```sql", "").replace("```", "")

        if post_process:
            content = post_process(content)

        usage = result.usage_metadata
        return content, usage.get("output_tokens", 0), usage.get("input_tokens", 0)

    def extract_entities(
        self, question: str, agent_definition: str, CongressionalDistrict_flag: bool
    ):
        """
        Uses an identifier agent to extract entities from the question and fetch data concurrently.

        Args:
            question (str): Input query.
            agent_definition (str): Prompt for the identifier agent.
            CongressionalDistrict_flag (bool): Toggle for congressional data.

        Returns:
            tuple: Extracted entity lists and token counts.
        """
        prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate(input_variables=[], template=agent_definition)
                ),
                HumanMessagePromptTemplate(
                    prompt=PromptTemplate(input_variables=[], template="{input}")
                ),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )

        identifier_agent = prompt | self.llm
        result = identifier_agent.invoke(
            {
                "input": question,
                "CongressionalDistrict_flag": CongressionalDistrict_flag,
            }
        )

        extracts = result.content
        usage = result.usage_metadata
        output_tokens = usage.get("output_tokens", 0)
        input_tokens = usage.get("input_tokens", 0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_supplier = executor.submit(
                self.generic_retriever,
                extracts,
                "suppliers",
                supplier_index,
                "No match found",
            )
            future_taxonomy = executor.submit(
                self.generic_retriever,
                extracts,
                "taxonomy",
                taxonomy_index,
                "No match found",
            )
            future_units = executor.submit(
                self.generic_retriever, extracts, "units", unit_index, "No match found"
            )

            future_bu_geographics = executor.submit(
                self.generic_retriever,
                extracts,
                "BU",
                businessunits_index,
                "No match found",
            )
            future_rig_name = executor.submit(
                self.generic_retriever,
                extracts,
                "RigName",
                rigname_index,
                "No match found",
            )
            future_csid = executor.submit(
                self.generic_retriever, extracts, "CSID", csid_index, "No match found"
            )

            future_congress_spend = executor.submit(
                self.generic_retriever,
                extracts,
                "CongressSpend",
                CongressionalDistrict_index,
                "No match found",
            )

            supplier_list = future_supplier.result()
            taxonomy_list = future_taxonomy.result()
            units_list = future_units.result()
            bu_geographics_list = future_bu_geographics.result()
            rig_name_list = future_rig_name.result()
            csid_list = future_csid.result()
            congress_spend_list = future_congress_spend.result()

        return (
            taxonomy_list,
            bu_geographics_list,
            rig_name_list,
            supplier_list,
            congress_spend_list,
            units_list,
            csid_list,
            output_tokens,
            input_tokens,
        )
