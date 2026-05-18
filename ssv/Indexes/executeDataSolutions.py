# Databricks notebook source
dbutils.widgets.dropdown('environment', 'dev', ['dev', 'test', 'prod'])
environment = dbutils.widgets.get('environment')

# COMMAND ----------

data_solutions = [
  # Views with 0 dependencies
  'CombinedSpend', 'RigPerformance', 'UserLogs', 'SCALE', 'CongressionalDistrict', 
  'WellCost', 'WellCostCompletion', 'WellCostPCE', 'CombinedContracts', 'GEPOrders',
  
  # Views with plus1 dependency
  'RigCost'
]


# COMMAND ----------

for file in data_solutions:
  try:
    dbutils.notebook.run(f"/releases/DataSolution/{file}.py", 1000, {'environment':environment})
  except Exception as e:
    print(f'{file} failed to run. \nError: {e}')
