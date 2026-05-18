# Databricks notebook source
import detk 
from pyspark.sql.functions import col, coalesce, lit, sum, min, max, lower, when, regexp_replace, year, month, count_distinct, sha2
import datetime as dt

tk=detk.Detk(secret_location = 'dbsecrets')

# COMMAND ----------

cols_to_index=["RigName",'RigContractor']

# COMMAND ----------

dbutils.widgets.dropdown('environment', 'dev', ['dev', 'test', 'prod'])

# COMMAND ----------

cvx_environment = dbutils.widgets.get('environment')
dls_env = '' if cvx_environment == 'prod' else cvx_environment

# COMMAND ----------

dls=tk.Data.connect_datalake(datalake_name=f"chevrondatalake{dls_env}")
adls= dls.get_container_path(container= "produced")

# COMMAND ----------

rig_perf = dls.spark_session.read.parquet(f"{adls}PSCM/SSV/RigPerformance")

not_loaded = True
days_offset = 1
while not_loaded and days_offset < 45:
    offset_date = dt.datetime.now() - dt.timedelta(days=days_offset)
    try:
        combined_spend = dls.spark_session.read.parquet(f"{adls}/PSCM/CombinedSpend/Global/v2/Full/{offset_date.year:04d}/{offset_date.month:02d}/{offset_date.day:02d}/*/**")
        print(f"Offset Days: {days_offset}")
        not_loaded = False
    except Exception as e:  
        print(e)
        days_offset += 1


# COMMAND ----------

rig_cost = rig_perf.alias('rp').join(
    combined_spend.alias('cs'), col('cs.WBSElementID') == regexp_replace(col('rp.AFENumber'), '-', '')
)

# COMMAND ----------

rig_cost = rig_cost.select(
    'RigContractor', 'RigName', 'WellName', 'ActualDuration', 'AFENumber', 'GlobalUpstreamOrganization', 'BusinessUnit',  'CountryName', 'Area', 'StateProvince', 'CountyParish', 'FieldName', 'GoverningAuthority', 'CurrentOperator', 'LateralLength', 'SupplierName', 'ContractID', 'ChevronTaxonomyLevel1', 'ChevronTaxonomyLevel2', 'ChevronTaxonomyLevel3', 'ChevronTaxonomyLevel4', 'Description', 'ApprovedDate', 'UnitOfMeasure',rig_perf['StartDate'],'AmountAfterDiscountUSD', 'WBSElementID','MaxJobEndDate','L3ShortBU','SourceableSpend','Intercompany','UnitPriceUSD'
).filter(col('ChevronTaxonomyLevel2')=="Rigs")

# COMMAND ----------

for col_name in cols_to_index:
    rig_cost = rig_cost.withColumn(f"{col_name}GUID", sha2(col(col_name), 256))

# COMMAND ----------

now = dt.datetime.now()
rec_date, rec_month, rec_year = now.day, now.month, now.year
adls_path= dls.get_container_path(container= "refined")
rig_cost.write.mode("overwrite").format("parquet").save(f"{adls_path}/PSCM/SSV/{now.year:04d}/{now.month:02d}/{now.day:02d}/RigCost")

# COMMAND ----------

rig_cost=rig_cost.withColumn("BU",col('L3ShortBU'))

# COMMAND ----------

adls_path= dls.get_container_path(container= "produced")
rig_cost.write.mode("overwrite").format("parquet").save(f"{adls_path}/PSCM/SSV/RigCost")
rig_cost.write.mode("overwrite").format("parquet").partitionBy("BU").save(f"{adls_path}/PSCM/SSV/RigCostPartitioned")
