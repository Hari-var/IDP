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
from app.benchmark import start_benchmarking, run_manual_benchmark
# from app.email_func import send_email_notification
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import logging
import json
from datetime import datetime
import uuid

app = FastAPI()

# Configure structured logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        return json.dumps(log_entry)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Set JSON formatter for file handler
file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(JSONFormatter())

# Keep simple format for console
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)
logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# Prometheus metrics - use try/except to avoid duplicate registration
try:
    REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
    PROCESSING_TIME = Histogram('document_processing_seconds', 'Document processing time')
    DOCUMENT_COUNT = Counter('documents_processed_total', 'Total documents processed', ['doc_type'])
    
    # AI-specific Prometheus metrics
    AI_REQUEST_COUNT = Counter('ai_requests_total', 'Total AI requests', ['model', 'operation'])
    AI_LATENCY = Histogram('ai_request_duration_seconds', 'AI request latency', ['model', 'operation'])
    AI_TOKEN_COUNT = Counter('ai_tokens_total', 'Total AI tokens used', ['model', 'type'])
    AI_ERROR_COUNT = Counter('ai_errors_total', 'Total AI errors', ['model', 'error_type'])
    AI_CONFIDENCE_SCORE = Histogram('ai_confidence_score', 'AI model confidence scores', ['model', 'operation'])
except ValueError:
    # Metrics already registered, get existing ones
    from prometheus_client import REGISTRY
    REQUEST_COUNT = REGISTRY._names_to_collectors['http_requests_total']
    PROCESSING_TIME = REGISTRY._names_to_collectors['document_processing_seconds']
    DOCUMENT_COUNT = REGISTRY._names_to_collectors['documents_processed_total']
    AI_REQUEST_COUNT = REGISTRY._names_to_collectors['ai_requests_total']
    AI_LATENCY = REGISTRY._names_to_collectors['ai_request_duration_seconds']
    AI_TOKEN_COUNT = REGISTRY._names_to_collectors['ai_tokens_total']
    AI_ERROR_COUNT = REGISTRY._names_to_collectors['ai_errors_total']
    AI_CONFIDENCE_SCORE = REGISTRY._names_to_collectors['ai_confidence_score']

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["*"] for all (not safe in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Start benchmarking system
start_benchmarking()

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
async def process_document(file: UploadFile = File(...),source:str=Form("API")):
    request_id = str(uuid.uuid4())
    REQUEST_COUNT.labels(method='POST', endpoint='/process/').inc()
    
    logger.info("Document upload initiated", extra={
        'extra_data': {
            "request_id": request_id,
            "event_type": "document_upload_start",
            "filename": file.filename,
            "source": source,
            "file_size": file.size if hasattr(file, 'size') else None
        }
    })
    
    try:
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        main(file_location, source, request_id)
        
        logger.info("Document processing completed successfully", extra={
            'extra_data': {
                "request_id": request_id,
                "event_type": "document_processing_success",
                "filename": file.filename,
                "status": "success"
            }
        })
        
        return {"message": f"File '{file.filename}' processed successfully.", "request_id": request_id}
    except Exception as e:
        logger.error("Document processing failed", extra={
            'extra_data': {
                "request_id": request_id,
                "event_type": "document_processing_error",
                "filename": file.filename,
                "error": str(e),
                "error_type": type(e).__name__
            }
        })
        return {"error": str(e), "request_id": request_id}


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

def main(file_path, source, request_id=None):
    process_file(file_path, source, request_id)

def process_file(file_path, source, request_id=None):
    file_name = os.path.basename(file_path)
    start_time = time.time()
    
    logger.info("File processing started", extra={
        'extra_data': {
            "request_id": request_id,
            "event_type": "file_processing_start",
            "file_name": file_name,
            "file_path": file_path,
            "source": source
        }
    })
    
    with PROCESSING_TIME.time():
        extracted_text = operation(file_path, source)
    
    # Convert list to string if needed
    if isinstance(extracted_text, list):
        text_content = str(extracted_text)
    else:
        text_content = extracted_text
    
    # AI Classification with metrics tracking
    ai_start_time = time.time()
    AI_REQUEST_COUNT.labels(model='gemini', operation='classification').inc()
    
    try:
        # Use actual AI call with metrics
        doc_type, summary = get_gemini_response_with_context(text_content)
        
    except Exception as e:
        AI_ERROR_COUNT.labels(model='gemini', error_type=type(e).__name__).inc()
        doc_type, summary = "error", "Classification failed"
        
    processing_time_ms = int((time.time() - start_time) * 1000)
    full_path = os.path.abspath(file_path)
    
    insert_document_log(file_name, source, doc_type, processing_time_ms, summary, full_path, use_azure=False)
    DOCUMENT_COUNT.labels(doc_type=doc_type).inc()
    
    # Professional structured log entry
    logger.info("Document classification completed", extra={
        'extra_data': {
            "request_id": request_id,
            "event_type": "document_classification",
            "file_name": file_name,
            "source": source,
            "doc_type_predicted": doc_type,
            "processing_time_ms": processing_time_ms,
            "file_size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else None,
            "extraction_method": "OCR",
            "confidence_score": confidence_score if 'confidence_score' in locals() else None
        }
    })
    
    if doc_type.strip().lower() == "other":
        logger.warning("Manual classification required", extra={
            'extra_data': {
                "request_id": request_id,
                "event_type": "manual_classification_required",
                "file_name": file_name,
                "doc_type": doc_type,
                "action_required": "manual_review"
            }
        })
    
    
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

@app.get("/metrics/ai")
def ai_metrics_json():
    """AI metrics in JSON format"""
    from prometheus_client import REGISTRY
    
    metrics_data = {
        "ai_requests_total": {},
        "ai_tokens_total": {},
        "ai_errors_total": {},
        "ai_request_duration_seconds": {},
        "benchmark_metrics": {}
    }
    
    # Collect AI metrics
    for metric_name, metric in REGISTRY._names_to_collectors.items():
        if metric_name.startswith('ai_'):
            if hasattr(metric, '_value'):
                # Counter/Gauge
                if hasattr(metric, '_labelnames') and metric._labelnames:
                    # Has labels
                    metric_values = {}
                    for sample in metric.collect()[0].samples:
                        label_key = '_'.join([f"{k}={v}" for k, v in zip(metric._labelnames, sample.labels)])
                        metric_values[label_key] = sample.value
                    metrics_data[metric_name] = metric_values
                else:
                    # No labels
                    metrics_data[metric_name] = metric._value._value
            elif hasattr(metric, '_sum'):
                # Histogram
                samples = list(metric.collect()[0].samples)
                histogram_data = {}
                for sample in samples:
                    if sample.name.endswith('_sum'):
                        histogram_data['sum'] = sample.value
                    elif sample.name.endswith('_count'):
                        histogram_data['count'] = sample.value
                metrics_data[metric_name] = histogram_data
        
        # Collect benchmark metrics
        elif metric_name.startswith('benchmark_'):
            if hasattr(metric, '_value'):
                if hasattr(metric, '_labelnames') and metric._labelnames:
                    metric_values = {}
                    for sample in metric.collect()[0].samples:
                        label_key = '_'.join([f"{k}={v}" for k, v in zip(metric._labelnames, sample.labels)])
                        metric_values[label_key] = sample.value
                    metrics_data["benchmark_metrics"][metric_name] = metric_values
                else:
                    metrics_data["benchmark_metrics"][metric_name] = metric._value._value
    
    return metrics_data

@app.get("/logs")
def get_logs(lines: int = 100):
    """Get recent application logs"""
    try:
        with open('app.log', 'r') as f:
            log_lines = f.readlines()
        return {"logs": log_lines[-lines:]}
    except FileNotFoundError:
        return {"logs": ["No log file found"]}

@app.get("/benchmark/run")
def run_benchmark():
    """Run benchmark test manually"""
    run_manual_benchmark()
    return {"message": "Benchmark test completed. Check benchmark.log for results."}

@app.get("/benchmark/results")
def get_benchmark_results():
    """Get all benchmark results"""
    try:
        with open('benchmark_results.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"message": "No benchmark results found"}

@app.get("/benchmark/results/latest")
def get_latest_benchmark_results():
    """Get latest benchmark results only"""
    try:
        with open('benchmark_results.json', 'r') as f:
            all_results = json.load(f)
            return all_results[-1] if all_results else {"message": "No results found"}
    except FileNotFoundError:
        return {"message": "No benchmark results found"}

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
            # Convert email files using existing functions
            if ext == ".msg":
                output_pdf_path = convert_msg_to_pdf(file_path)
            else:
                output_pdf_path = convert_eml_to_pdf(file_path)

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
