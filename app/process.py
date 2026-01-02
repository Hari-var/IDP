from json import loads
import os
from pathlib import Path
import time 
import random
from fastapi import FastAPI, File, UploadFile,Form,Query
import shutil
from app.llm import get_gemini_response_with_context
from  app.sql import insert_document_log,get_doc_type_count,query_get_avg_processing_time,get_recent_documents,get_source_options,get_details_by_id,update_document_by_id,delete_document_by_id
from app.extraction import operation
# from app.email_func import send_email_notification
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import logging
import json

app = FastAPI()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
PROCESSING_TIME = Histogram('document_processing_seconds', 'Document processing time')
DOCUMENT_COUNT = Counter('documents_processed_total', 'Total documents processed', ['doc_type'])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["*"] for all (not safe in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def make_permalink(id):
   
    url = f"/viewer?file_id={id}"
    return f'<a href="{url}" target="_self">{id}</a>'

from fastapi import Query, HTTPException
from fastapi.responses import FileResponse
import tempfile
import subprocess
import fitz  # PyMuPDF (optional for conversion validation)
import extract_msg
import email
from email import policy
from email.parser import BytesParser




def convert_to_pdf(input_path: str) -> str:
    """
    Converts office-like files (.docx, .pptx, .xlsx, etc.) to PDF using LibreOffice.
    """
    output_dir = tempfile.mkdtemp()
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, input_path],
        check=True
    )
    base_name = Path(input_path).stem + ".pdf"
    return os.path.join(output_dir, base_name)


def convert_msg_to_pdf(msg_path: str) -> str:
    """
    Converts an Outlook .msg file to PDF.
    """
    msg = extract_msg.Message(msg_path)
    content = f"From: {msg.sender}\nTo: {msg.to}\nSubject: {msg.subject}\n\n{msg.body}"
    
    pdf_path = os.path.join(tempfile.gettempdir(), Path(msg_path).stem + ".pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def convert_eml_to_pdf(eml_path: str) -> str:
    """
    Converts an .eml file to PDF (basic body text).
    """
    with open(eml_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    
    body = msg.get_body(preferencelist=('plain',))
    text = body.get_content() if body else "(No content)"
    header = f"From: {msg['From']}\nTo: {msg['To']}\nSubject: {msg['Subject']}\n\n"
    content = header + text

    pdf_path = os.path.join(tempfile.gettempdir(), Path(eml_path).stem + ".pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@app.post("/process/")
async def process_document(file: UploadFile = File(...),source:str=Form("API")):#File(...) makes sure that the file is uploaded as part of the request parameters
    REQUEST_COUNT.labels(method='POST', endpoint='/process/').inc()
    logger.info(f"Processing document: {file.filename}, source: {source}")
    try:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        # full_path = os.path.abspath(file_location)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Call your main function with the saved file path
        main(file_location,source)
        logger.info(f"Document processed successfully: {file.filename}")
        return {"message": f"File '{file.filename}' processed successfully."}
    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        return {"error": str(e)}


@app.get("/get_doc_types/")
async def get_doc_types():
    """
    Endpoint to retrieve document types.
    """
    REQUEST_COUNT.labels(method='GET', endpoint='/get_doc_types/').inc()
    df=get_doc_type_count()
    
    # This function should return the list of document types
    # For now, we will return a static list as an example
    return df.to_dict(orient="records")

def main(file_path,source):
    print("main function called")
    process_file(file_path,source)


def process_file(file_path,source):# Extract the file name from the path
    logger.info(f"Starting file processing: {file_path}")
    file_name = os.path.basename(file_path)
    print(file_path)  
    print(f"Document Name: {file_name}")
    # source=random.choice(source_options)  # Randomly select a source from the options
    start_time = time.time()
    with PROCESSING_TIME.time():
        extracted_text = operation(file_path,source)
    print(extracted_text)
    # Convert list to string if needed
    if isinstance(extracted_text, list):
        text_content = str(extracted_text)
    else:
        text_content = extracted_text
    doc_type,summary="other",text_content[:150] #get_gemini_response_with_context(extracted_text)
    # print(f"Predicted Document Type: {doc_type}")
    # print("++++++++++++++++++++++++++++++++++++++}")
    # print(f"Summary: {summary}")
    processing_time_ms = int((time.time() - start_time) * 1000)
    full_path = os.path.abspath(file_path)
    insert_document_log(file_name, source, doc_type, processing_time_ms, summary, full_path, use_azure=False)
    DOCUMENT_COUNT.labels(doc_type=doc_type).inc()
    
    # Structured log entry
    log_data = {
        "event": "document_processed",
        "file_name": file_name,
        "source": source,
        "doc_type": doc_type,
        "processing_time_ms": processing_time_ms,
        "file_path": full_path
    }
    logger.info(json.dumps(log_data))
    
    if doc_type.strip().lower() == "other":
        logger.warning(f"Document requires manual classification: {file_name}")
        # send_email_notification(file_name, source, doc_type)
        print(f"Document '{file_name}' requires manual classification/handling.")
        
    print(f"{file_name}Document processed successfully!")
    
    
@app.get("/get_sources/")
async def get_sources():
    """
    Endpoint to retrieve sources.
    """
    source_options = get_source_options()  # This should be replaced with a database query if needed
    return source_options
    
    
@app.get("/get_avg_processing_time/")
async def get_avg_processing_time():
    """
    Endpoint to retrieve average processing time by document type.
    """
    
    df=query_get_avg_processing_time()
    
    return df.to_dict(orient="records")

@app.get("/recent_documents/")
def recent_documents(
    selected_source: Optional[str] = Query(None),
    selected_doc_type: Optional[str] = Query(None),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None),
    file_name_input: Optional[str] = Query(None),
    page_num: int = 1,
    page_size: int = 10
):
    date_range = [date_start, date_end] if date_start and date_end else []
    docs = get_recent_documents(selected_source, selected_doc_type, date_range, file_name_input, page_num, page_size)
    docs['file_id'] = docs['id'].apply(make_permalink)
    return docs.to_dict(orient="records")

@app.get("/get_details_by_id/{file_id}")
def process_get_details_by_id(file_id: int):
    """
    Endpoint to retrieve details of a document by its ID.
    """
    df = get_details_by_id(file_id)
    print(df)
    # if df.empty:
    #     return {"message": "No document found with the given ID."}
    return df.to_dict(orient="records")[0]

from fastapi import Body, HTTPException
from fastapi.responses import FileResponse

@app.put("/update_document_by_id/{file_id}")
def process_update_document_by_id(
    file_id: int,
    data: dict = Body(...)
):
    """
    Endpoint to update a document by its ID.
    Expects JSON with keys: file_name, prediction, summary, source
    """
    # Extract fields from the incoming JSON
    file_name = data.get("file_name")
    prediction = data.get("prediction")
    summary = data.get("summary")
    source = data.get("source")

    # Call your SQL update function (adjust as needed)
    result = update_document_by_id(
        file_id,
        prediction,
        summary,
        source
    )
    if result:
        return {"message": "Document updated successfully."}
    return {"message": "Failed to update document."}

@app.delete("/delete_document_by_id/{file_id}")
def process_delete_document_by_id(file_id: int):
    """
    Endpoint to delete a document by its ID.
    """
    result = delete_document_by_id(file_id)
    if result:
        return {"message": "Document deleted successfully."}
    return {"message": "Failed to delete document."}

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/logs")
def get_logs(lines: int = 100):
    """Get recent application logs"""
    try:
        with open('app.log', 'r') as f:
            log_lines = f.readlines()
        return {"logs": log_lines[-lines:]}
    except FileNotFoundError:
        return {"logs": ["No log file found"]}

"""@app.get("/view_document/{file_id}")
def view_document(file_id: int):
    
    doc_details = get_details_by_id(file_id)
    if doc_details.empty:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc_details.iloc[0]['file_path']
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(Path(file_path))"""

@app.get("/view_document/{file_id}")
def view_document(file_id: int):
    doc_details = get_details_by_id(file_id)
    if doc_details.empty:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc_details.iloc[0]['file_path']
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    ext = Path(file_path).suffix.lower()

    # If the file is already viewable (PDF or image), just return it
    if ext in [".pdf", ".jpg", ".jpeg", ".png", ".tiff"]:
        return FileResponse(file_path, media_type="application/pdf", headers={"Content-Disposition": "inline"})

    # If it's a DOCX, MSG, or EML → Convert to PDF
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            output_pdf_path = tmp_pdf.name

        if ext == ".docx":
            # Convert DOCX → PDF using LibreOffice (must be installed)
            subprocess.run([
                "soffice", "--headless", "--convert-to", "pdf", "--outdir",
                os.path.dirname(output_pdf_path), file_path
            ], check=True)
            converted_file = Path(file_path).with_suffix(".pdf")
            if not converted_file.exists():
                raise Exception("DOCX conversion failed")
            os.rename(converted_file, output_pdf_path)

        elif ext in [".msg", ".eml"]:
            # Convert email files → PDF (via pandoc)
            pypandoc.convert_file(file_path, "pdf", outputfile=output_pdf_path)

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

        return FileResponse(output_pdf_path, media_type="application/pdf", headers={"Content-Disposition": "inline"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")
    
# from fastapi.responses import StreamingResponse
# import mimetypes

# @app.get("/view_document/{file_id}")
# def view_document(file_id: int):
#     """
#     Endpoint to serve a document file by its ID.
#     """
#     doc_details = get_details_by_id(file_id)
#     if doc_details.empty:
#         raise HTTPException(status_code=404, detail="Document not found")

#     file_path = doc_details.iloc[0]['file_path']
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found")
    
#     # Determine media type
#     media_type, _ = mimetypes.guess_type(file_path)
#     if not media_type:
#         media_type = 'application/octet-stream'
    
#     def iterfile():
#         with open(file_path, mode="rb") as file:
#             yield from file
    
#     return StreamingResponse(
#         iterfile(),
#         media_type=media_type,
#         headers={"Content-Disposition": "inline"}
#     )

from fastapi import Query

@app.get("/view_document1")
def view_document1(path: str = Query(...)):
    """
    Endpoint to serve a document file by its path.
    """
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    
    ext = os.path.splitext(path)[1].lower()
    media_type = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.tiff': 'image/tiff'
    }.get(ext, 'application/octet-stream')
    
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Content-Disposition": "inline"}
    )
