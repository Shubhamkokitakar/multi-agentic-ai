# Databricks notebook source
# DBTITLE 1,Import the libraries
import detk
from pyspark.sql.functions import sha2, col, coalesce, lit, sum, min, max, lower, when, concat, regexp_replace, to_date,to_timestamp, explode, split, year, avg, expr,count
from pyspark.sql import Window   
from functools import reduce
import datetime as dt
from pyspark.sql import functions as F

tk=detk.Detk(secret_location = 'dbsecrets')

# COMMAND ----------

# DBTITLE 1,Widget for environment
dbutils.widgets.dropdown('environment', 'dev', ['dev', 'test', 'prod'])

# COMMAND ----------

# DBTITLE 1,Variables
cvx_environment = dbutils.widgets.get('environment')
dls_env = '' if cvx_environment == 'prod' else cvx_environment

# COMMAND ----------

dls=tk.Data.connect_datalake(datalake_name=f"chevrondatalake{dls_env}")
adls= dls.get_container_path(container= "produced")

# COMMAND ----------

# DBTITLE 1,Import the WellView data
def safe_read(path):
    try:
        return  dls.spark_session.read.parquet(f"{adls}/{path}")
    except Exception as e:
        print(f"Error reading data from folder {path}")
        return None

ListOfBUs = ['MCBU','SJV']

rig_list = [safe_read(f"Wells/DrillingJob/{BU}/Rig/v1/**") for BU in ListOfBUs]
rig = reduce(lambda df1, df2: df1.union(df2), [x for x in rig_list if x is not None])

phase_list = [safe_read(f"Wells/DrillingJob/{BU}/Phase/v1/**") for BU in ListOfBUs]
phase = reduce(lambda df1, df2: df1.union(df2), [x for x in phase_list if x is not None])

job_list = [safe_read(f"Wells/DrillingJob/{BU}/Job/v2/**") for BU in ListOfBUs]
job = reduce(lambda df1, df2: df1.union(df2), [x for x in job_list if x is not None])

BOP_list = [safe_read(f"Wells/DrillingJob/{BU}/BOP/v1/**") for BU in ListOfBUs]
BOP = reduce(lambda df1, df2: df1.union(df2), [x for x in BOP_list if x is not None])

wh_list = [safe_read(f"Wells/WellDataBasic/{BU}/WellHeader/v2/**") for BU in ListOfBUs]
well_header = reduce(lambda df1, df2: df1.union(df2), [x for x in wh_list if x is not None])

wellbore_list = [safe_read(f"Wells/WellDataBasic/{BU}/Wellbore/v2/**") for BU in ListOfBUs]
well_bore = reduce(lambda df1, df2: df1.union(df2), [x for x in wellbore_list if x is not None])

tubularAssembly_list = [safe_read(f"Wells/Tubular/{BU}/TubularAssembly/v2/**") for BU in ListOfBUs]
tubular_assembly = reduce(lambda df1, df2: df1.union(df2), [x for x in tubularAssembly_list if x is not None])

stim_list = [safe_read(f"Wells/Completions/{BU}/Stimulation/v2/**") for BU in ListOfBUs]
stimulation = reduce(lambda df1, df2: df1.union(df2), [x for x in stim_list if x is not None])

kd_list = [safe_read(f"Wells/WellDataBasic/{BU}/KeyDepth/v1/**") for BU in ListOfBUs]
key_depth = reduce(lambda df1, df2: df1.union(df2), [x for x in kd_list if x is not None])

# COMMAND ----------

# DBTITLE 1,Import Combined Spend data
not_loaded = True
days_offset = 1
while not_loaded and days_offset < 45:
    offset_date = dt.datetime.now() - dt.timedelta(days=days_offset)
    try:
        combined_spend = dls.spark_session.read.parquet(f"{adls}/PSCM/CombinedSpend/Global/v2/Full/{offset_date.year:04d}/{offset_date.month:02d}/{offset_date.day:02d}/*/**"
        )
        print(f"Offset Days: {days_offset}")
        not_loaded = False
    except:
        days_offset += 1
        print(f"Offset Days: {days_offset}")

# COMMAND ----------

# DBTITLE 1,Select required columns
#well header
well_header= well_header.select("WellID","HostFacilityName","WellName","SurfaceUniqueWellIdentifier","Area","FieldName").filter(col("SurfaceUniqueWellIdentifier") != '0000000000')

#rig
rig = (
    rig.select('WellID', 'RigContractor', 'RigType', 'CreationDateTime', 'RigName','RigID')
    .filter(col('RigType').rlike('(?i)drilling rig'))
    .dropDuplicates()
    .withColumn('RigName', when(col('RigName').contains(col('RigContractor')), col('RigName'))
                .otherwise(concat(col('RigContractor'), lit(' '), col('RigName'))))
)


#phase 
phase=phase.select('WellID', 'ActualStartDate', 'ActualEndDate', 'PhaseCode2','ActualDuration','RigID','DepthProgressActual','PlanDetails','PhaseID','PlannedAFECost')

# job
job_base = job.select(
    'WellID', 
    regexp_replace('AuthorizationForExpenditureNumber', '-', '').alias('AuthorizationForExpenditureNumber'),
    'BusinessUnitFolder',
    'SpudDateTime',
    col('StartDateTime').alias('JobStartDate'),  # Replace with your desired name for StartDateTime
    col('EndDateTime').alias('JobEndDate')      # Replace with your desired name for EndDateTime
).dropDuplicates()

# bop
BOP = BOP.select(
    'WellID','EndDate'
)

#well_bore
well_bore = well_bore.select('WellID', 'DrillStartDateTime', 'DrillEndDateTime') \
    .drop_duplicates() \
    .withColumn('DrillStartDateTime', to_date(col('DrillStartDateTime'))) \
    .withColumn('DrillEndDateTime', to_date(col('DrillEndDateTime'))) \
    .groupBy('WellID') \
    .agg(
        min(col('DrillStartDateTime')).alias('DrillStartDate'),
        max(col('DrillEndDateTime')).alias('DrillEndDate')
    ) \
    .withColumn(
    'CenterDate',
    expr("date_add(DrillStartDate, cast(datediff(DrillEndDate, DrillStartDate) / 2 as int))")
     ).filter(col('CenterDate').isNotNull())
    
#stimulation
stimulation_summary = stimulation.filter(col('StartDateTime') >= '2020-01-01')
stimulation_summary = stimulation_summary.select('WellID', 'TotalCleanVolume', 'GrossLength', 'TotalProppant').drop_duplicates().groupBy('WellID').agg(max(col('TotalCleanVolume')).alias('MaxTotalCleanVolume'), max(col('GrossLength')).alias('MaxGrossLength'), max(col('TotalProppant')).alias('MaxTotalProppant'))

#tubalarAssembly
tubular_assembly = tubular_assembly.select('WellID', 'TubularDescription').dropna(subset=['TubularDescription']).drop_duplicates().withColumn('contains_intermediate_casing_2', col('TubularDescription').rlike('(?i)intermediate casing 2').cast('int')).groupby('WellID').agg(sum('contains_intermediate_casing_2').alias('contains_intermediate_casing_2'))
tubular_assembly = tubular_assembly.withColumn('welldesign', when(col('contains_intermediate_casing_2') > 0, '4string').otherwise('3string')).select('WellID', 'welldesign').drop_duplicates()

# COMMAND ----------

welldata_merged = (
    job_base
    .join(well_header, on='WellID', how='left')
    .dropDuplicates()
    .join(well_bore, on='WellID', how='left')
    .join(BOP, on='WellID', how='left')
)

# COMMAND ----------

# DBTITLE 1,Exploding AFE Numbers
welldata_merged  = welldata_merged.withColumn(
    "AuthorizationForExpenditureNumber",
    F.when(
        F.col("AuthorizationForExpenditureNumber").isNotNull() & (F.size(F.split(F.col("AuthorizationForExpenditureNumber"), ";")) > 0),
        F.expr("transform(split(AuthorizationForExpenditureNumber, ';'), x -> x)")
    ).otherwise(F.array(F.col("AuthorizationForExpenditureNumber")))
)
welldata_merged  = welldata_merged.withColumn(
    "AuthorizationForExpenditureNumber",
    F.explode_outer(F.col("AuthorizationForExpenditureNumber"))
).withColumn('DrillEndDate', F.to_date('DrillEndDate')).filter(F.col('DrillEndDate') > '2021-01-01').drop_duplicates()

# COMMAND ----------

# DBTITLE 1,Calculating Drilled Depth
job_drilled_depth = job.select(
    'AuthorizationForExpenditureNumber', 
    'DrillingWellCategory', 
    'DrilledDepth'
).drop_duplicates()

job_drilled_depth = job_drilled_depth.withColumn(
    'AuthorizationForExpenditureNumber', 
    F.regexp_replace('AuthorizationForExpenditureNumber', '-', '')
).withColumn(
    "AuthorizationForExpenditureNumber",
    F.when(
        F.col("AuthorizationForExpenditureNumber").isNotNull() & (F.col("AuthorizationForExpenditureNumber") != ""), 
        F.split(F.col("AuthorizationForExpenditureNumber"), ";")
    ).otherwise(F.array(F.col("AuthorizationForExpenditureNumber")))
).withColumn(
    "AuthorizationForExpenditureNumber", 
    F.explode_outer(F.col("AuthorizationForExpenditureNumber"))
)

window_spec = Window.partitionBy("AuthorizationForExpenditureNumber").orderBy(F.col("DrilledDepth").desc())

job_drilled_depth = job_drilled_depth.groupBy(
    "AuthorizationForExpenditureNumber", 
    "DrillingWellCategory"
).agg(
    F.sum("DrilledDepth").alias("DrilledDepth")
).withColumn(
    "row_num", 
    F.row_number().over(window_spec)
).filter(
    F.col("row_num") == 1
).drop(
    "row_num"
).dropDuplicates()

# COMMAND ----------

welldata_merged = (
    welldata_merged
    .join(job_drilled_depth,on='AuthorizationForExpenditureNumber',how='left')
    .join(tubular_assembly,on='WellID',how='left')
    )

# COMMAND ----------

# DBTITLE 1,Calculating TargetFormation
job_drill = job.dropDuplicates().withColumn('AuthorizationForExpenditureNumber',regexp_replace(col('AuthorizationForExpenditureNumber'), '-', '')).filter(col('PrimaryJobType') == 'Drill and Suspend')
job_drill_formation = job_drill.select('WellID', 'TargetFormation')
job_drill_formation = job_drill_formation.filter( 
    ~job_drill_formation['TargetFormation'].isin( [0,'None','0',0])
).dropDuplicates()


# COMMAND ----------

# DBTITLE 1,Calculating Actual Duration
# Filter and add default values for ActualDuration and PlannedAFECost
phase_ad = phase.where(
    (col('ActualEndDate').isNotNull()) & 
    (col('ActualStartDate').isNotNull()) & 
    (col('PhaseCode2').isNotNull()) & 
    (col('RigID').isNotNull())
).withColumn(
    'ActualDuration', coalesce(col('ActualDuration'), lit(0))
).withColumn(
    'PlannedAFECost', coalesce(col('PlannedAFECost'), lit(0))
)

# Group by WellID and calculate aggregates, including ActualStartDate and ActualEndDate
phase_ad = phase_ad.groupBy('WellID').agg(
    sum('ActualDuration').alias('ActualDuration'),
    sum(when(col('PhaseCode2') == 'DRILL', col('ActualDuration')).otherwise(0)).alias('DrillDuration'),
    min('ActualStartDate').alias('ActualStartDate'),
    max('ActualEndDate').alias('ActualEndDate')
)

# COMMAND ----------

# DBTITLE 1,Calculating Lateral Length
stimulation_ll = stimulation.withColumn(
        'GrossLength', coalesce(col('GrossLength'), lit(0))
    ).groupBy('WellID').agg(
        sum(col("GrossLength")).alias('GrossLength')
    )

phase_ll = phase.filter(lower(col("PlanDetails")).contains("drill lateral")).select('WellID', 'PhaseID', 'DepthProgressActual').withColumn('DepthProgressActual', coalesce(col('DepthProgressActual'), lit(0)))
phase_ll = phase_ll.groupBy('WellID').agg(max('DepthProgressActual').alias('DepthProgressActual'))

keydepth_ll = key_depth.groupBy('WellID').agg(
    (max(when(col('Type') == 'Toe', col('TopDepth'))).alias('ToeDepth') - 
     max(when(col('Type') == 'Heel', col('TopDepth'))).alias('HeelDepth')).alias('LateralLength')
)

lateral_length = keydepth_ll.join(
        phase_ll, on='WellID', how='outer'
    ).join(
        stimulation_ll, on='WellID', how='outer'
    ).withColumn(
        'LateralLength', coalesce(col('DepthProgressActual'), col('LateralLength'), col('GrossLength'))
    ).select('WellID', 'LateralLength')

# COMMAND ----------

rig = rig.withColumn("CreationDateTime", F.to_timestamp("CreationDateTime"))
window_spec = Window.partitionBy("WellID").orderBy(F.col("CreationDateTime").desc())
rig = rig.withColumn("row_num", F.row_number().over(window_spec)).filter(F.col("row_num") == 1).drop("row_num")

# COMMAND ----------

welldata_merged = (welldata_merged 
    .join(phase_ad, on='WellID', how='left')
    .join(job_drill_formation, on='WellID', how='left')
    .join(stimulation_summary, on='WellID', how='left')
    .join(rig, on='WellID', how='left')
    .join(lateral_length, on='WellID', how='left')
    .filter(
        (col('AuthorizationForExpenditureNumber').isNotNull()) & 
        (col('AuthorizationForExpenditureNumber') != "")
    )
)

# COMMAND ----------

combined_spend = combined_spend.select(
    "AmountAfterDiscountUSD", "SupplierPartNumber", "CSIDSupplier", "Description", "WBSElementID", "UnitPriceUSD", "UnitofMeasure", "Quantity", "AribaDocumentNumber", "SupplierInvoiceNumber", "ContractID", "BUSubcategory","ApprovedDate",'L5BU','ChevronTaxonomyLevel1', 'ChevronTaxonomyLevel2', 'ChevronTaxonomyLevel3'
)

# COMMAND ----------

well_cost = combined_spend.join(welldata_merged, combined_spend["WBSElementID"] == welldata_merged["AuthorizationForExpenditureNumber"], "inner")

# Remove duplicates
well_cost = well_cost.select('ContractID', 'RigID', 'AmountAfterDiscountUSD', 'BUSubcategory', 'SupplierPartNumber', 'CSIDSupplier', 'Description', 'WBSElementID', 'UnitPriceUSD', 'UnitofMeasure', 'Quantity', 'AribaDocumentNumber', 'SupplierInvoiceNumber', 'LateralLength', 'WellID', 'AuthorizationForExpenditureNumber', 'HostFacilityName', 'WellName', 'SurfaceUniqueWellIdentifier', 'Area', 'BusinessUnitFolder', 'FieldName', 'RigName', 'RigContractor', 'RigType', 'CreationDateTime', 'CenterDate', 'DrillStartDate', 'DrillEndDate', 'DrillingWellCategory', 'DrilledDepth', 'WellDesign', 'ActualDuration', 'DrillDuration', 'TargetFormation', 'MaxTotalCleanVolume', 'MaxGrossLength', 'MaxTotalProppant','ChevronTaxonomyLevel1', 'ChevronTaxonomyLevel2', 'ChevronTaxonomyLevel3').dropDuplicates(subset=["AmountAfterDiscountUSD","DrillEndDate","AribaDocumentNumber","SupplierInvoiceNumber","ContractID","SupplierPartNumber"]).withColumnRenamed("DrilledDepth","DrilledDepthInFeet")

# COMMAND ----------

# DBTITLE 1,write to refined
now = dt.datetime.now()
rec_date, rec_month, rec_year = now.day, now.month, now.year
adls_path= dls.get_container_path(container= "refined")
well_cost.write.mode("overwrite").format("parquet").save(f"{adls_path}/PSCM/SSV/{now.year:04d}/{now.month:02d}/{now.day:02d}/WellCost")

# COMMAND ----------

well_cost=well_cost.withColumn("BU",col('BusinessUnitFolder'))

# COMMAND ----------

adls_path= dls.get_container_path(container= "produced")
well_cost.write.mode("overwrite").format("parquet").save(f"{adls_path}/PSCM/SSV/WellCost")
well_cost.write.mode("overwrite").format("parquet").partitionBy("BU").save(f"{adls_path}/PSCM/SSV/WellCostPartitioned")

