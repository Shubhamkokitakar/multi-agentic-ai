import re
import json
import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from babel.numbers import format_currency
from config.config import *
from utils.logger import logger


class SQLHelper:
    def __init__(self):
        
        self.server = os.environ.get("SYNAPSE_SERVER")
        self.database = "ssv-ia"
        self.username = str(os.environ.get("SYNAPSE_USERNAME"))
        self.password = os.environ.get("SYNAPSE_PASSWORD")
        self.Session = self.initiate_sql_session()


    def initiate_sql_session(self):
        """
        Creates and returns a SQLAlchemy sessionmaker for the SQL Server database.

        Returns:
            sessionmaker: A configured SQLAlchemy session factory.
        """
        connection_url = URL.create(
            drivername="mssql+pyodbc",
            username=self.username,
            password=self.password,
            host=self.server,
            port=1433,
            database=self.database,
            query={"driver": "ODBC Driver 17 for SQL Server"},
        )
        engine = create_engine(connection_url)
        return sessionmaker(bind=engine)

    def execute_sql_query(self, query, suppliers):
        """
        Cleans and executes a SQL query with supplier parameters, returning results as a DataFrame.

        Args:
            query (str): The raw SQL query string.
            suppliers (list): List of supplier values to clean and inject into the query.

        Returns:
            pd.DataFrame: Query results as a DataFrame.
        """
        query = self.clean_query(query, suppliers)
        query, params = self.extract_values(query)
        with self.Session() as session:
            logger.info("Executing Query")
            result = session.execute(text(query), params)
            logger.info("Execution Successful")
            return pd.DataFrame(result.all(), columns=result.keys())

    def remove_all_suppliernameguid_like(self, query):
        """
        Removes all 'SupplierNameGUID LIKE' conditions from the given SQL query string.

        Args:
            query (str): SQL query string.

        Returns:
            str: Query string with 'SupplierNameGUID LIKE' clauses removed.
        """
        pattern = r"SupplierNameGUID\s+LIKE\s+'[^']+'\s+(OR|AND\s+)?"
        return re.sub(pattern, "", query)

    def clean_query(self, query, suppliers):
        """
        Cleans and modifies the SQL query by replacing 'SupplierNameGUID LIKE' patterns 
        with an 'IN' clause using the given suppliers list.

        Args:
            query (str): Original SQL query string.
            suppliers (list): List of supplier identifiers.

        Returns:
            str: Modified SQL query string.
        """
        query = query.replace("\\'", "''")
        if "SupplierNameGUID LIKE '%" in query:
            suppliers = str(tuple(suppliers))
            if suppliers[-2:] == ",)":
                suppliers = suppliers[:-2] + suppliers[-1]
            start = query.rfind("SupplierNameGUID LIKE '%")
            end = query.find("%", start + 25)
            supplier = query[start + 16 : end + 2]
            query = query.replace(supplier, f" IN {suppliers}")
            query = self.remove_all_suppliernameguid_like(query)
        return query

    def extract_values(self, input_string):
        """
        Extracts quoted string values from the input and replaces them with parameter placeholders.

        Args:
            input_string (str): The input string containing quoted values.

        Returns:
            tuple: 
                - Modified string with placeholders (str)
                - Dictionary mapping placeholders to original values (dict)
        """
        values = {}
        start = 0
        while True:
            start = input_string.find(" :", start)
            if start == -1:
                break
            left_quote = input_string.rfind("'", 0, start)
            right_quote = input_string.find("'", start + 2)
            if left_quote == -1 or right_quote == -1:
                break
            value = input_string[left_quote + 1 : right_quote]
            input_string = input_string.replace(
                input_string[left_quote : right_quote + 1],
                f":param{len(values)}",
            )
            values[f"param{len(values)}"] = value
            start = right_quote + 1
        return input_string, values


class DataFormatter:
    @staticmethod
    def add_space_to_column_names(column_name):
        """
        Inserts spaces into a camelCase or PascalCase column name between words and numbers.

        Args:
            column_name (str): The camelCase or PascalCase column name.

        Returns:
            str: The column name with spaces inserted between words and digits.
        """
        return re.sub(
            r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[a-zA-Z])(?=[0-9])|(?<=[0-9])(?=[a-zA-Z])",
            " ",
            column_name,
        )

    @staticmethod
    def clean_and_format_df(df, apply_currency=False):
        """
        Cleans and formats a DataFrame by fixing dates, numeric columns, and applying optional currency formatting.

        Args:
            df (pd.DataFrame): Input DataFrame to clean.
            apply_currency (bool): If True, apply currency formatting.

        Returns:
            list[dict] | None: Cleaned DataFrame as list of dicts, or None if input is empty or None.
        """
        if df is None or df.empty:
            return None

        df = df.replace(["None", "nan"], np.nan)
        for column in df.columns:
            try:
                if "date" in column.lower():
                    df[column] = df[column].astype(str)
                elif column.lower() == "year":
                    df[column] = pd.to_datetime(df[column], format="%Y").dt.strftime(
                        "%Y"
                    )
                elif "month" in column.lower():
                    try:
                        df[column] = pd.to_numeric(df[column])
                        if pd.api.types.is_float_dtype(df[column]):
                            df[column] = df[column].round(2)
                            logger.info(
                                f"Rounded month column '{column}': {df[column].head()}"
                            )
                        else:
                            logger.info(
                                f"Column '{column}' could not be converted to numeric."
                            )
                    except ValueError as ve:
                        logger.error(f"ValueError in column '{column}': {ve}")
                        df[column] = (
                            df[column].astype(str).apply(DataFormatter.convert_month)
                        )
                        logger.info(
                            f"Converted non-numeric month values in '{column}': {df[column].head()}"
                        )
                else:
                    pd.options.display.float_format = "{:.2f}".format
                    df[column] = pd.to_numeric(df[column])

            except Exception as e:
                logger.error(f"Error processing column '{column}': {str(e)}")
                continue


        df.columns = [
            DataFormatter.add_space_to_column_names(col) for col in df.columns
        ]
        df.index = range(1, len(df) + 1)
        
        df = (
                df.replace("", pd.NA)
                .replace([np.nan, pd.NaT],pd.NA)
                .dropna(how="all")
                .drop_duplicates()
                )

        if apply_currency:
            df = DataFormatter.format_currency_in_df(df)
            df = df.where(pd.notnull(df), None).replace(pd.NA,"None")
            return df.to_dict(orient="records")
        else:
            return df.to_dict(orient="records")

    @staticmethod
    def format_currency_in_df(df):
        """
        Format numeric DataFrame columns with currency or decimal formatting
        based on column name keywords.

        Args:
            df (pd.DataFrame): Input DataFrame.

        Returns:
            pd.DataFrame: DataFrame with formatted currency/decimal strings.
        """
        currency_keywords = ["cost", "spend", "price", "amount", "spent"]
        non_currency_keywords = ["percentage", "year", "month", "percent","quarter","id"]

        for column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                try:
                    if any(k in column.lower() for k in currency_keywords) and not any(
                        nk in column.lower() for nk in non_currency_keywords
                    ):
                        df[column] = df[column].apply(
                            lambda x: (
                                format_currency(
                                    x,
                                    currency="USD",
                                    locale="en_US",
                                    format="¤#,##0.00",
                                    currency_digits=False,
                                )
                                if pd.notnull(x)
                                else x
                            )
                        )
                    else:
                        if not any(nk in column.lower() for nk in non_currency_keywords):
                            df[column] = df[column].apply(
                                lambda x: f"{x:,.2f}" if pd.notnull(x) else x
                            )
                except Exception as e:
                    logger.info(f"{e} for {column}")
        return df

    @staticmethod
    def generate_data_profile(df):
        """
        Generate aggregated stats grouped by categorical columns and descriptive stats.

        Args:
            df (pd.DataFrame): Input DataFrame.

        Returns:
            tuple: (grouped_agg_df or None, descriptive_stats_dict)
        """
        df = df.dropna()
        for column in df.columns:
            try:
                if "date" not in column.lower() and column.lower() != "year":
                    df.loc[:, column] = pd.to_numeric(df[column])
                    logger.info(f"Successfully converted {column} to numeric")
            except Exception as e:
                logger.info(f"Error converting {column} to numeric: {e}")

        numerical = df.select_dtypes(include=["number"]).columns.tolist()
        categorical = [col for col in df.columns if col not in numerical]

        logger.info(f"Categorical: {categorical}, Numerical: {numerical}")

        try:
            if categorical and numerical:
                agg_funcs = [
                    "min",
                    "max",
                    "median",
                    "mean",
                    "std",
                    "var",
                    "sum",
                    "count",
                ]
                result = df.groupby(categorical)[numerical].agg(agg_funcs).reset_index()

                try:
                    data_desc = result.describe(include="object").T.to_dict(
                        orient="records"
                    )

                except Exception as e:
                    data_desc = {}
                    logger.info(f"Descriptive error in grouped result: {str(e)}")

                return result, data_desc

            else:
                logger.info("Insufficient columns for aggregation")

                try:
                    data_desc = df.describe(include="object").T.to_dict(
                        orient="records"
                    )
                except Exception as e:
                    data_desc = {}
                    logger.info(f"Descriptive error: {str(e)}")

                return None, data_desc

        except Exception as e:
            logger.info(f"Data profile error: {str(e)}")

            try:
                data_desc = df.describe(include="all").T.to_dict(orient="records")

            except Exception as inner_e:
                logger.info(f"Final descriptive error: {str(inner_e)}")
                data_desc = {}

            return None, data_desc

    @staticmethod
    def convert_month(value):
        """
        Convert numeric month or 'YYYY-MM' string to abbreviated month or 'YYYY-MMM' format.

        Args:
            value (int|str): Month as int/string or year-month string.

        Returns:
            str|original value: Converted month string or original if conversion fails.
        """
        try:
            if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
                return datetime.datetime.strptime(str(value), "%m").strftime("%b")
            elif isinstance(value, str) and "-" in value:
                return pd.to_datetime(value, format="%Y-%m").strftime("%Y-%b")
        except Exception as e:
            logger.info(f"Error converting month: {e}")
        return value