import os
import sqlite3
import pyodbc
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"Base directory set to: {BASE_DIR}")
DB_PATH = os.path.join(BASE_DIR, "synthetic.db")
print(f"Database path set to: {DB_PATH}")

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Azure SQL connection settings from environment
AZURE_SQL_CONFIG = {
    "server": os.getenv("AZURE_SQL_SERVER"),
    "database": os.getenv("AZURE_SQL_DATABASE"),
    "username": os.getenv("AZURE_SQL_USERNAME"),
    "password": os.getenv("AZURE_SQL_PASSWORD"),
    "driver": os.getenv("AZURE_SQL_DRIVER")
}

def get_azure_sql_connection():
    conn_str = (
        f"DRIVER={AZURE_SQL_CONFIG['driver']};"
        f"SERVER={AZURE_SQL_CONFIG['server']},1433;"
        f"DATABASE={AZURE_SQL_CONFIG['database']};"
        f"UID={AZURE_SQL_CONFIG['username']};"
        f"PWD={AZURE_SQL_CONFIG['password']}"
    )
    return pyodbc.connect(conn_str)