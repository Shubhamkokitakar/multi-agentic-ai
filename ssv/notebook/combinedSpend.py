# Databricks notebook source
# DBTITLE 1,Import the libraries
import detk 
from pyspark.sql.functions import sha2, col, when, lit
import datetime as dt

tk=detk.Detk(secret_location = 'dbsecrets')
cols_to_index = ['SupplierName', 'ChevronTaxonomyLevel1', 'ChevronTaxonomyLevel2', 'ChevronTaxonomyLevel3', 'ChevronTaxonomyLevel4', 'L3ShortBU', 'L3LongBU','L4BU', 'L5BU',
'BUMDMRegion', 'BUMDMCountry', 'Address', 'BUCategory', 'BUSubcategory', 'EnterpriseCategory', 'PlantName', 'BusinessUnitID','UnitOfMeasure',"CSIDSupplier","CSIDParent"]

# COMMAND ----------

# DBTITLE 1,Widget for environment
dbutils.widgets.dropdown('environment', 'dev', ['dev', 'test', 'prod'])

# COMMAND ----------

cvx_environment = dbutils.widgets.get('environment')
dls_env = '' if cvx_environment == 'prod' else cvx_environment

# COMMAND ----------

dls=tk.Data.connect_datalake(datalake_name=f"chevrondatalake{dls_env}")
adls_path= dls.get_container_path(container= "produced")


# COMMAND ----------

# DBTITLE 1,Import the data
not_loaded = True
days_offset = 1
while not_loaded and days_offset < 45:
    offset_date = dt.datetime.now() - dt.timedelta(days=days_offset)
    try:

        combined_spend= dls.spark_session.read.parquet(f"{adls_path}/PSCM/CombinedSpend/Global/v2/Full/{offset_date.year:04d}/{offset_date.month:02d}/{offset_date.day:02d}/*/**")
        print(f"Offset Days: {days_offset}")
        not_loaded = False
    except Exception as e:  
        days_offset += 1


# COMMAND ----------

# DBTITLE 1,Required Columns Selection
combined_spend = combined_spend.select([
    'FactCombinedSpendBK', 'L3ShortBU','L5BU','L4BU', 'L3LongBU', 'BusinessUnitID', 'BUCategory', 'BUSubcategory', 'CSIDSupplier', 'SupplierName', 'ContractID', 'Description', 'ApprovedDate', 'Quantity', 'UnitOfMeasure', 'UnitPriceTransCurrency', 'CurrencySymbol', 'AmountAfterDiscountUSD', 'UnitPriceUSD', 'SourceableSpend', 'Intercompany', 'WBSElementID', 'ChevronTaxonomyLevel1', 'ChevronTaxonomyLevel2', 'ChevronTaxonomyLevel3', 'ChevronTaxonomyLevel4','AmountDate', 'BUMDMRegion', 'BUMDMCountry', 'Address', 'CreateDate', 'EnterpriseCategory', 'PlantName', 'SupplierID', 'SupplierInvoiceNumber', 'CSIDParent', 'WBSProjectTypeDesc', 'AribaDocumentNumber', 'CompanyCodeID', 'ProductOrService', 'ContractIndicator', 'DocumentType', 'NetDaysDue','StartDate','CatalogIndicator','SupplierPartNumber','CommodityCodeDesc'

    ]).filter(col('ApprovedDate')!='1999-12-31T00:00:00.000+00:00')

# COMMAND ----------

# DBTITLE 1,Data Modifications
combined_spend=combined_spend.withColumn("CapexorOpex", when(col('WBSProjectTypeDesc') == 'Capital', lit('capex')).when(col('SourceableSpend') != 'Capital', lit('opex'))).withColumn("InterCompany",when(col("InterCompany") == "Y", "Y").otherwise("N"))

# COMMAND ----------

# DBTITLE 1,Create GUID columns
for col_name in cols_to_index:
    combined_spend = combined_spend.withColumn(f"{col_name}GUID", sha2(col(col_name), 256))

# COMMAND ----------

# DBTITLE 1,write to refined
now = dt.datetime.now()
rec_date, rec_month, rec_year = now.day, now.month, now.year
adls_path= dls.get_container_path(container= "refined")
combined_spend.write.mode("overwrite").format("parquet").save(f"{adls_path}/PSCM/SSV/{now.year:04d}/{now.month:02d}/{now.day:02d}/CombinedSpend")

# COMMAND ----------

# DBTITLE 1,Create col for Partitioning
combined_spend=combined_spend.withColumn("BU",col('L3ShortBU'))

# COMMAND ----------

# DBTITLE 1,write to Prodused
adls_path= dls.get_container_path(container= "produced")
combined_spend.write.mode("overwrite").format("parquet").save(f"{adls_path}/PSCM/SSV/CombinedSpend")
combined_spend.write.mode("overwrite").format("parquet").partitionBy("BU").save(f"{adls_path}/PSCM/SSV/CombinedSpendPartitioned")
