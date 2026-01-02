# from config import get_azure_sql_connection,DB_PATH
# import sqlite3

# # from app.config import DB_PATH, get_azure_sql_connection

# def get_connection(use_azure=False):
#     """
#     Returns a database connection.
#     Set use_azure=True to use Azure SQL, otherwise uses local SQLite.
#     """
#     if use_azure:
#         return get_azure_sql_connection()
#     return sqlite3.connect(DB_PATH)

# def print_azure_tables():
#     conn = get_azure_sql_connection()
#     cursor = conn.cursor()
#     cursor.execute("SELECT name FROM sys.tables;")
#     tables = cursor.fetchall()
#     print("Tables in Azure SQL database:")
#     for table in tables:
#         print(table[0])
#     conn.close()
    
# def table_exists(table_name="document_logs", use_azure=False):
#     conn = get_connection(use_azure)
#     cursor = conn.cursor()
#     if use_azure:
#         cursor.execute("SELECT name FROM sys.tables WHERE name=?;", (table_name,))
#     else:
#         cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
#     exists = cursor.fetchone() is not None
#     conn.close()
#     return exists

# def create_table_if_not_exists(use_azure=False):
#     if not table_exists("document_logs", use_azure):
#         conn = get_connection(use_azure)
#         cursor = conn.cursor()
#         if use_azure:
#             process_info = """
#             IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='document_logs' and xtype='U')
#             CREATE TABLE document_logs (
#                 id INT IDENTITY(1,1) PRIMARY KEY,
#                 document_name NVARCHAR(255),
#                 timestamp DATETIME DEFAULT GETDATE(),
#                 source NVARCHAR(255),
#                 doc_type_predicted NVARCHAR(255),
#                 processing_time_ms INT,
#                 summary NVARCHAR(MAX),
#                 file_path NVARCHAR(1024)
#             );
#             """
#         else:
#             process_info = """
#             CREATE TABLE IF NOT EXISTS document_logs (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 document_name TEXT,
#                 timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
#                 source TEXT,
#                 doc_type_predicted TEXT,
#                 processing_time_ms INTEGER,
#                 summary TEXT,
#                 file_path TEXT
#             );
#             """
#         cursor.executescript(process_info) if not use_azure else cursor.execute(process_info)
#         conn.commit()
#         conn.close()

# # if __name__ == "__main__":
# #     print_azure_tables()
# #     create_table_if_not_exists(use_azure=True)