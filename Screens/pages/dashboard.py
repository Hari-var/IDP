import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os
import urllib.parse
# from app.config import DB_PATH
import requests

# Page config
st.set_page_config(page_title="IDP Document Dashboard", layout="wide")

# Sidebar
# st.sidebar.title("IDP Dashboard")
# st.sidebar.info("Monitor document processing and analytics.")

# Main Title
st.title("📄 Intelligent Document Processing Dashboard")
st.markdown("---")


# Connect to database
# conn = sqlite3.connect(DB_PATH)  
# cursor = conn.cursor()



#Calling API to get document types
response= requests.get(
    "http://localhost:8000/get_doc_types/"
            )
data=response.json()  # This gives you the JSON data returned by FastAPI
df = pd.DataFrame(data)
if df.empty:
    st.warning("No document types found.")
else:
    st.subheader("Predicted Document Type Frequency")
    st.dataframe(df, use_container_width=True)
st.markdown("---")

# Pie Chart and Average Processing Time by Document Type side by side

#Api call to get average processing time by document type
response_avg = requests.get(
    "http://localhost:8000/get_avg_processing_time/"
)
data_avg = response_avg.json()  # This gives you the JSON data returned by FastAPI
df_avg = pd.DataFrame(data_avg)


st.subheader("Document Type Distribution & Avg. Processing Time")
col1, col2 = st.columns(2)

#Pie Chart for Document Type Distribution
with col1:
    if df.empty:
        st.warning("No document data found for pie chart.")
    else:
        fig, ax = plt.subplots()
        ax.pie(df['count'], labels=df['doc_type_predicted'], autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)

with col2:
    if df_avg.empty:
        st.warning("No data for average processing time.")
    else:
        st.bar_chart(df_avg.set_index('doc_type_predicted')['avg_time'])
st.markdown("---")


# Fetch unique values for filters
#API call to get sources and document types
response_sources = requests.get("http://localhost:8000/get_sources/")
sources = response_sources.json()   
# This gives you the JSON data returned by FastAPI
doc_types=df['doc_type_predicted'].dropna().unique().tolist()


st.subheader("Recent Document Processing Activity")

# Streamlit filter widgets
col1, col2, col3 = st.columns(3)
with col1:
    selected_source = st.selectbox("Source", ["All"] + sources)
with col2:
    selected_doc_type = st.selectbox("Document Type", ["All"] + doc_types)
with col3:
    date_range = st.date_input("Date Range", [])
col1,col2 = st.columns(2)
with col1:   
    file_name_input = st.text_input("Search by File Name")

# Build query with filters
# query = "SELECT * FROM document_logs WHERE 1=1"
# params = []

# if selected_source != "All":
#     query += " AND source = ?"
#     params.append(selected_source)
# if selected_doc_type != "All":
#     query += " AND doc_type_predicted = ?"
#     params.append(selected_doc_type)
# if date_range and len(date_range) == 2:
#     query += " AND DATE(timestamp) BETWEEN ? AND ?"
#     params.append(str(date_range[0]))
#     params.append(str(date_range[1]))

# if file_name_input:
#     query += " AND document_name LIKE ?"
#     params.append(f"%{file_name_input}%")


# query += " ORDER BY timestamp DESC LIMIT 100"

# df_recent = pd.read_sql_query(query, conn, params=params)
  
# df_recent['file_id'] = df_recent['id'].apply(make_permalink)

with col2:
    PAGE_SIZE = st.number_input(
        "Rows per page", min_value=1, max_value=100, value=3, step=1, key="page_size"
    )
# st.write(df_recent.to_html(escape=False, index=False), unsafe_allow_html=True)
  # Number of rows per page
# total_rows = len(df_recent)
# total_pages = (total_rows // PAGE_SIZE) + int(total_rows % PAGE_SIZE > 0)

# if total_pages > 1:
#     page_num = st.number_input(
#         "Page", min_value=1, max_value=total_pages, value=1, step=1, key="page_num"
#     )
# else:
#     page_num = 1

# start_idx = (page_num - 1) * PAGE_SIZE
# end_idx = start_idx + PAGE_SIZE
# df_page = df_recent.iloc[start_idx:end_idx]
# df_page=df_page.drop(columns=['id','file_path'])  # Drop the 'id' column for display
# df_page.index = range(start_idx + 1, start_idx + 1 + len(df_page))
# st.write(df_page.to_html(escape=False, index=True), unsafe_allow_html=True)




# # File upload field for supported document types
# st.markdown("---")
# conn.close()

    # You can add further processing logic here
    
    
page_num = st.number_input(
    "Page", min_value=1, value=1, step=1, key="page_num"
)

params = {
    "selected_source": selected_source,
    "selected_doc_type": selected_doc_type,
    "date_start": str(date_range[0]) if date_range and len(date_range) == 2 else None,
    "date_end": str(date_range[1]) if date_range and len(date_range) == 2 else None,
    "file_name_input": file_name_input,
    "page_num": page_num,
    "page_size": PAGE_SIZE
}
response = requests.get("http://localhost:8000/recent_documents/", params=params)
df_page = pd.DataFrame(response.json())
df_page=df_page.drop(columns=['id','file_path'])  # Drop the 'id' column for display
st.write(df_page.to_html(escape=False, index=True), unsafe_allow_html=True)