# # import sqlite3
# # import pandas as pd
# # # Connect to SQLite
# # from app.config import DB_PATH,get_azure_sql_connection
# # print(f"Connecting to database at: {DB_PATH}")
# # conn = sqlite3.connect(DB_PATH)
# # # conn = sqlite3.connect(DB_PATH)
# # cursor = conn.cursor()
# # from app.config import get_azure_sql_connection




# # def table_exists(table_name="document_logs"):
# #     # conn = sqlite3.connect(db_path)
# #     conn = get_azure_sql_connection()
# #     cursor = conn.cursor()
# #     cursor.execute("""
# #         SELECT name FROM sys.tables WHERE name=?;
# #     """, (table_name,))
# #     exists = cursor.fetchone() is not None
# #     conn.close()
# #     return exists

# # # Usage example:
# # if table_exists("document_logs"):
# #     print("Table exists!")
# # else:
# #     print("Table does not exist.")
# # # Create table with auto-increment ID
# #     process_info = """
# #     CREATE TABLE IF NOT EXISTS document_logs (
# #         id INTEGER PRIMARY KEY AUTOINCREMENT,
# #         document_name TEXT,
# #         timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
# #         source TEXT,
# #         doc_type_predicted TEXT,
# #         processing_time_ms INTEGER,
# #         summary TEXT,
# #         file_path TEXT
        
# #     );
# #     """

# #     # Execute the query
# #     cursor.execute(process_info)
# #     conn.commit()
# #     conn.close()

# #     print("Table created with auto-incrementing ID.")


# # def insert_document_log(document_name, upload, response, processing_time_ms, summary,file_path):
# #     conn = sqlite3.connect(DB_PATH)
# #     cursor = conn.cursor()
# #     insert_query = """
# #         INSERT INTO document_logs (document_name, source, doc_type_predicted, processing_time_ms, summary,file_path)
# #         VALUES (?, ?, ?, ?, ?,?);
# #     """
# #     cursor.execute(insert_query, (document_name, upload, response, processing_time_ms, summary,file_path))
# #     conn.commit()
# #     conn.close()
    
# # def delete_all_document_logs():
# #     conn = sqlite3.connect(DB_PATH)
# #     cursor = conn.cursor()
# #     cursor.execute("DELETE FROM document_logs;")
# #     conn.commit()
# #     conn.close()
# #     print("All document logs deleted successfully.")
# # # delete_all_document_logs()

# # def get_details_by_id(file_id):
# #     conn = sqlite3.connect(DB_PATH)
# #     query = "SELECT * FROM document_logs WHERE id=?"
# #     df = pd.read_sql_query(query, conn, params=(file_id,))
# #     conn.close()
# #     return df

# # def update_document_by_id(id, doc_type_predicted, summary, source):
# #     print(f"Updating document with ID {id}...")
# #     conn = sqlite3.connect(DB_PATH)
# #     cursor = conn.cursor()
# #     update_query = """
# #         UPDATE document_logs
# #         SET  doc_type_predicted=?, summary=?, source=?
# #         WHERE id=?;
# #     """
# #     cursor.execute(update_query, ( doc_type_predicted, summary, source, id))
# #     conn.commit()
# #     conn.close()
# #     print(f"Document with ID {id} updated successfully.")

# # def delete_document_by_id(id):
# #     print(f"Deleting document with ID {id}...")
# #     conn = sqlite3.connect(DB_PATH)
# #     cursor = conn.cursor()
# #     delete_query = "DELETE FROM document_logs WHERE id=?;"
# #     cursor.execute(delete_query, (id,))
# #     conn.commit()
# #     conn.close()
# #     print(f"Document with ID {id} deleted successfully.")

# # def get_doc_type_count():
# #     """
# #     Function to retrieve document types from the database.
# #     Returns a DataFrame with document types.
# #     """
# #     conn = sqlite3.connect(DB_PATH)
# #     df = pd.read_sql_query("SELECT doc_type_predicted, COUNT(*) as count FROM document_logs GROUP BY doc_type_predicted order by count DESC", conn)
# #     conn.close()
# #     return df

# # def query_get_avg_processing_time():
# #     """
# #     Function to retrieve average processing time by document type.
# #     Returns a DataFrame with document types and their average processing times.
# #     """
# #     conn = sqlite3.connect(DB_PATH)
# #     query_avg = """
# #         SELECT doc_type_predicted, AVG(processing_time_ms) as avg_time
# #         FROM document_logs
# #         GROUP BY doc_type_predicted
# #         ORDER BY doc_type_predicted ASC;
# #     """
    
# #     df_avg = pd.read_sql_query(query_avg, conn)
# #     conn.close()
# #     return df_avg
# # def get_recent_documents(selected_source=None, selected_doc_type=None, date_range=None, file_name_input=None, page_num=1, page_size=10):
# #     """
# #     Function to retrieve recent documents from the database with filters and pagination.
# #     Returns a list of dicts.
# #     """
# #     conn = sqlite3.connect(DB_PATH)
# #     query = "SELECT * FROM document_logs WHERE 1=1"
# #     params = []

# #     if selected_source and selected_source != "All":
# #         query += " AND source = ?"
# #         params.append(selected_source)
# #     if selected_doc_type and selected_doc_type != "All":
# #         query += " AND doc_type_predicted = ?"
# #         params.append(selected_doc_type)
# #     if date_range and len(date_range) == 2 and date_range[0] and date_range[1]:
# #         query += " AND DATE(timestamp) BETWEEN ? AND ?"
# #         params.append(str(date_range[0]))
# #         params.append(str(date_range[1]))
# #     if file_name_input:
# #         query += " AND document_name LIKE ?"
# #         params.append(f"%{file_name_input}%")

# #     query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
# #     params.extend([page_size, (page_num - 1) * page_size])

# #     df_recent = pd.read_sql_query(query, conn, params=params)
# #     conn.close()
# #     return df_recent

# # def get_source_options():
# #     """
# #     Function to retrieve unique source options from the database.
# #     Returns a list of unique sources.
# #     """
# #     conn = sqlite3.connect(DB_PATH)
# #     query = "SELECT DISTINCT source FROM document_logs"
# #     df_sources = pd.read_sql_query(query, conn)
# #     conn.close()
# #     return df_sources['source'].dropna().tolist()



# import os
# import sqlite3
# import pandas as pd
# from app.helpers.config import DB_PATH, get_azure_sql_connection


# def get_connection(use_azure=False):
#     """
#     Returns a database connection.
#     Set use_azure=True to use Azure SQL, otherwise uses local SQLite.
#     """
#     if use_azure:
#         return get_azure_sql_connection()
#     return sqlite3.connect(DB_PATH)

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

# def insert_document_log(document_name, upload, response, processing_time_ms, summary, file_path, use_azure=False):
#     conn = get_connection(use_azure)
#     cursor = conn.cursor()
#     if use_azure:
#         insert_query = """
#             INSERT INTO document_logs (document_name, source, doc_type_predicted, processing_time_ms, summary, file_path)
#             VALUES (?, ?, ?, ?, ?, ?);
#         """
#     else:
#         insert_query = """
#             INSERT INTO document_logs (document_name, source, doc_type_predicted, processing_time_ms, summary, file_path)
#             VALUES (?, ?, ?, ?, ?, ?);
#         """
#     cursor.execute(insert_query, (document_name, upload, response, processing_time_ms, summary, file_path))
#     conn.commit()
#     conn.close()

# def delete_all_document_logs(use_azure=False):
#     conn = get_connection(use_azure)
#     cursor = conn.cursor()
#     cursor.execute("DELETE FROM document_logs;")
#     conn.commit()
#     conn.close()

# def get_details_by_id(file_id, use_azure=False):
#     conn = get_connection(use_azure)
#     query = "SELECT * FROM document_logs WHERE id=?"
#     df = pd.read_sql_query(query, conn, params=(file_id,))
#     conn.close()
#     return df

# def update_document_by_id(id, doc_type_predicted, summary, source, use_azure=False):
#     conn = get_connection(use_azure)
#     cursor = conn.cursor()
#     update_query = """
#         UPDATE document_logs
#         SET doc_type_predicted=?, summary=?, source=?
#         WHERE id=?;
#     """
#     cursor.execute(update_query, (doc_type_predicted, summary, source, id))
#     conn.commit()
#     conn.close()

# def delete_document_by_id(id, use_azure=False):
#     conn = get_connection(use_azure)
#     cursor = conn.cursor()
#     cursor.execute("DELETE FROM document_logs WHERE id=?;", (id,))
#     conn.commit()
#     conn.close()

# def get_doc_type_count(use_azure=False):
#     conn = get_connection(use_azure)
#     df = pd.read_sql_query(
#         "SELECT doc_type_predicted, COUNT(*) as count FROM document_logs GROUP BY doc_type_predicted ORDER BY count DESC",
#         conn
#     )
#     conn.close()
#     return df

# def query_get_avg_processing_time(use_azure=False):
#     conn = get_connection(use_azure)
#     query_avg = """
#         SELECT doc_type_predicted, AVG(processing_time_ms) as avg_time
#         FROM document_logs
#         GROUP BY doc_type_predicted
#         ORDER BY doc_type_predicted ASC;
#     """
#     df_avg = pd.read_sql_query(query_avg, conn)
#     conn.close()
#     return df_avg

# def get_recent_documents(selected_source=None, selected_doc_type=None, date_range=None, file_name_input=None, page_num=1, page_size=10, use_azure=False):
#     conn = get_connection(use_azure)
#     query = "SELECT * FROM document_logs WHERE 1=1"
#     params = []

#     if selected_source and selected_source != "All":
#         query += " AND source = ?"
#         params.append(selected_source)
#     if selected_doc_type and selected_doc_type != "All":
#         query += " AND doc_type_predicted = ?"
#         params.append(selected_doc_type)
#     if date_range and len(date_range) == 2 and date_range[0] and date_range[1]:
#         query += " AND DATE(timestamp) BETWEEN ? AND ?"
#         params.append(str(date_range[0]))
#         params.append(str(date_range[1]))
#     if file_name_input:
#         query += " AND document_name LIKE ?"
#         params.append(f"%{file_name_input}%")

#     if use_azure:
#         # SQL Server pagination syntax
#         query += " ORDER BY timestamp DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
#         params.extend([(page_num - 1) * page_size, page_size])
#     else:
#         # SQLite/MySQL/Postgres syntax
#         query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
#         params.extend([page_size, (page_num - 1) * page_size])

#     df_recent = pd.read_sql_query(query, conn, params=params)
#     conn.close()
#     return df_recent

# def get_source_options(use_azure=False):
#     conn = get_connection(use_azure)
#     query = "SELECT DISTINCT source FROM document_logs"
#     df_sources = pd.read_sql_query(query, conn)
#     conn.close()
#     return df_sources['source'].dropna().tolist()

# if __name__ == "__main__":
#     exists = table_exists("document_logs", use_azure=False)
#     if exists:
#         print("Table 'document_logs' exists in Azure SQL!")
#     else:
#         print("Table 'document_logs' does NOT exist in Azure SQL!")