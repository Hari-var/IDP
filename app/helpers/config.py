import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"Base directory set to: {BASE_DIR}")

# Load environment variables from .env file
load_dotenv()

# ============================================================
# PRIMARY DATABASE: RetoolDB PostgreSQL (Production)
# ============================================================
cloud_db = "postgresql+psycopg2://retool:npg_a2Dck4vBuXpH@ep-young-dust-afizvmne.c-2.us-west-2.retooldb.com/retool?sslmode=require"
print(f"✅ Using RetoolDB PostgreSQL for all data storage")

# ============================================================
# OPTIONAL: Azure SQL connection settings (Not used)
# ============================================================
AZURE_SQL_CONFIG = {
    "server": os.getenv("AZURE_SQL_SERVER"),
    "database": os.getenv("AZURE_SQL_DATABASE"),
    "username": os.getenv("AZURE_SQL_USERNAME"),
    "password": os.getenv("AZURE_SQL_PASSWORD"),
    "driver": os.getenv("AZURE_SQL_DRIVER")
}
endpoint = "https://idp-claims-4657894.cognitiveservices.azure.com/"
key = os.environ.get("doc_intelligence_key")

# def get_azure_sql_connection():
#     conn_str = (
#         f"DRIVER={AZURE_SQL_CONFIG['driver']};"
#         f"SERVER={AZURE_SQL_CONFIG['server']},1433;"
#         f"DATABASE={AZURE_SQL_CONFIG['database']};"
#         f"UID={AZURE_SQL_CONFIG['username']};"
#         f"PWD={AZURE_SQL_CONFIG['password']}"
#     )
#     return pyodbc.connect(conn_str)

MY_SAS_URL = os.getenv("sas_url")
CONTAINER_NAME = os.getenv("container_name")