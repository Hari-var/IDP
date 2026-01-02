# import streamlit as st

# st.title("📤 Upload Document")
# st.markdown("Upload a file of type: **jpg, png, tiff, pdf, docx, eml, msg**")

# allowed_types = ["jpg", "jpeg", "png", "tiff", "pdf", "docx", "eml", "msg"]

# uploaded_file = st.file_uploader(
#     "Choose a file",
#     type=allowed_types,
#     accept_multiple_files=False
# )

# if uploaded_file is not None:
#     st.success(f"File '{uploaded_file.name}' uploaded successfully!")
#     file_details = {
#         "filename": uploaded_file.name,
#         "filetype": uploaded_file.type,
#         "filesize": uploaded_file.size
#     }
#     st.write(file_details)
#     with open(f"uploaded_{uploaded_file.name}", "wb") as f:
#         f.write(uploaded_file.getbuffer())
#     st.info("File saved for processing.")

import streamlit as st
import requests
st.set_page_config(layout="wide")
st.title("📤 Upload Document")
st.markdown("Upload a file of type: **jpg, png, tiff, pdf, docx,xls, eml, msg**")

allowed_types = ["jpg", "jpeg", "png", "tiff", "pdf", "docx", "eml", "msg","xls"]

uploaded_file = st.file_uploader(
    "Choose a file",
    type=allowed_types,
    accept_multiple_files=False
)

if uploaded_file is not None:
    st.success(f"File '{uploaded_file.name}' uploaded successfully!")
    file_details = {
        "filename": uploaded_file.name,
        "filetype": uploaded_file.type,
        "filesize": uploaded_file.size
    }
    st.write(file_details)
    st.info("File ready for processing.")

    if st.button("Process File"):
        # Send the file to the FastAPI endpoint
        data = {"source": "Manual Upload"}
        files = {"file": (uploaded_file.name, uploaded_file.getbuffer())}
        response = requests.post(
    "http://localhost:8000/process/",
    files=files,
    data={"source": "Manual Upload"}
            )
        if response.status_code == 200:
            st.success("File processed successfully!")
            st.write(data)
            st.write(response.json())
        else:
            st.error(f"Processing failed: {response.text}")