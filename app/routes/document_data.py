import os
import time
import uuid
import shutil
from pathlib import Path
import tempfile
import subprocess
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from prometheus_client import Counter, Histogram, REGISTRY

from app.helpers.extraction import operation
from app.helpers.converters import convert_msg_to_pdf, convert_eml_to_pdf, convert_to_pdf
from app.helpers.azure_blob import upload_file_to_azure_blob, download_file_from_azure_blob
from app.helpers.llm import get_gemini_response_with_context
from app.helpers.logger import logger
from app.database.database import sessionlocal
from app.database.sql import (
    insert_document_log,
    get_details_by_id,
    update_document_by_id,
    get_recent_documents,
    get_source_options,
    get_doc_type_count,
    get_avg_processing_time,
    DocRequest,
    DocUpdateRequest
)

router = APIRouter(prefix="/document_data", tags=["Document Data"])

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
    REQUEST_COUNT = REGISTRY._names_to_collectors['http_requests_total']
    PROCESSING_TIME = REGISTRY._names_to_collectors['document_processing_seconds']
    DOCUMENT_COUNT = REGISTRY._names_to_collectors['documents_processed_total']
    AI_REQUEST_COUNT = REGISTRY._names_to_collectors['ai_requests_total']
    AI_LATENCY = REGISTRY._names_to_collectors['ai_request_duration_seconds']
    AI_TOKEN_COUNT = REGISTRY._names_to_collectors['ai_tokens_total']
    AI_ERROR_COUNT = REGISTRY._names_to_collectors['ai_errors_total']
    AI_CONFIDENCE_SCORE = REGISTRY._names_to_collectors['ai_confidence_score']

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ FILES STORED IN AZURE BLOB STORAGE
# All uploaded files are automatically stored in Azure Blob Storage with SAS URLs
# No local database - uses RetoolDB PostgreSQL for metadata


def process_file(file_path, source, request_id=None):
    """Process a file: extract text, classify with AI, and store in database."""
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
    
    try:
        with PROCESSING_TIME.time():
            extracted_text = operation(file_path, source)
        
        # Convert list to string if needed
        if isinstance(extracted_text, list):
            text_content = str(extracted_text)
        else:
            text_content = extracted_text
        
        # AI Classification with metrics tracking
        AI_REQUEST_COUNT.labels(model='gemini', operation='classification').inc()
        
        try:
            doc_type, summary = get_gemini_response_with_context(text_content)
        except Exception as e:
            AI_ERROR_COUNT.labels(model='gemini', error_type=type(e).__name__).inc()
            doc_type, summary = "error", "Classification failed"
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Upload to Azure Blob Storage using SAS URL
        try:
            file_url = upload_file_to_azure_blob(file_path, file_name)
            logger.info(f"✅ File uploaded to Azure Blob Storage: {file_name}")
            storage_type = "Azure Blob"
        except Exception as e:
            logger.error(f"Failed to upload to Azure Blob Storage: {str(e)}")
            # Fallback to local absolute path (not recommended for production)
            file_url = os.path.abspath(file_path)
            storage_type = "Local (Fallback)"
        
        # Store in database using SQLAlchemy
        db = sessionlocal()
        try:
            doc_request = DocRequest(
                document_name=file_name,
                source=source,
                doc_type_predicted=doc_type,
                processing_time_ms=processing_time_ms,
                summary=summary,
                file_url=file_url
            )
            insert_document_log(db, doc_request)
            DOCUMENT_COUNT.labels(doc_type=doc_type).inc()
        finally:
            db.close()
        
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
                "storage_type": storage_type
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
        
        return True
    
    except Exception as e:
        logger.error("File processing failed", extra={
            'extra_data': {
                "request_id": request_id,
                "event_type": "file_processing_error",
                "file_name": file_name,
                "error": str(e),
                "error_type": type(e).__name__
            }
        })
        raise


@router.post("/process/")
async def process_document(file: UploadFile = File(...), source: str = Form("API")):
    """Upload and process a document."""
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
        
        process_file(file_location, source, request_id)
        
        logger.info("Document processing completed successfully", extra={
            'extra_data': {
                "request_id": request_id,
                "event_type": "document_processing_success",
                "filename": file.filename,
                "status": "success"
            }
        })
        
        return {
            "message": f"File '{file.filename}' processed successfully.",
            "request_id": request_id
        }
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


@router.get("/recent_documents/")
def recent_documents(
    selected_source: Optional[str] = Query(None),
    selected_doc_type: Optional[str] = Query(None),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None),
    file_name_input: Optional[str] = Query(None),
    page_num: int = 1,
    page_size: int = 10
):
    """Get recent documents with filtering and pagination."""
    REQUEST_COUNT.labels(method='GET', endpoint='/recent_documents/').inc()
    
    date_range = [date_start, date_end] if date_start and date_end else []
    db = sessionlocal()
    try:
        docs = get_recent_documents(
            db,
            selected_source,
            selected_doc_type,
            date_range,
            file_name_input,
            page_num,
            page_size
        )
        
        # Convert to list of dicts
        result = []
        for doc in docs:
            doc_dict = {
                "id": doc.id,
                "document_name": doc.document_name,
                "source": doc.source,
                "doc_type_predicted": doc.doc_type_predicted,
                "processing_time_ms": doc.processing_time_ms,
                "summary": doc.summary,
                "file_url": doc.file_url,
                "timestamp": doc.timestamp
            }
            result.append(doc_dict)
        
        return result
    finally:
        db.close()


@router.get("/get_details_by_id/{file_id}")
def get_document_details(file_id: int):
    """Retrieve details of a document by its ID."""
    REQUEST_COUNT.labels(method='GET', endpoint='/get_details_by_id').inc()
    
    db = sessionlocal()
    try:
        doc = get_details_by_id(db, file_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "id": doc.id,
            "document_name": doc.document_name,
            "source": doc.source,
            "doc_type_predicted": doc.doc_type_predicted,
            "processing_time_ms": doc.processing_time_ms,
            "summary": doc.summary,
            "file_url": doc.file_url,
            "timestamp": doc.timestamp
        }
    finally:
        db.close()


@router.put("/update_document_by_id/{file_id}")
def update_document(file_id: int, data: dict):
    """Update a document by its ID."""
    REQUEST_COUNT.labels(method='PUT', endpoint='/update_document_by_id').inc()
    
    db = sessionlocal()
    try:
        doc_update = DocUpdateRequest(
            source=data.get("source"),
            doc_type_predicted=data.get("doc_type_predicted"),
            summary=data.get("summary")
        )
        
        result = update_document_by_id(db, doc_update, file_id)
        if result:
            return {"message": "Document updated successfully."}
        return {"message": "Failed to update document."}
    finally:
        db.close()


@router.get("/view_document/{file_id}")
def view_document(file_id: int):
    """View a document by its ID. If it's from Azure Blob Storage, redirect to the URL. Otherwise, download and convert if needed."""
    REQUEST_COUNT.labels(method='GET', endpoint='/view_document').inc()
    
    db = sessionlocal()
    try:
        doc = get_details_by_id(db, file_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        file_url = str(doc.file_url)  # Convert SQLAlchemy Column to string
        
        # If it's an Azure Blob Storage URL (contains .blob.core.windows.net), redirect to it
        if ".blob.core.windows.net" in file_url:
            logger.info(f"Redirecting to Azure Blob Storage URL for document {file_id}")
            return RedirectResponse(url=file_url, status_code=302)
        
        # Otherwise, it's a local path - handle file conversion if needed
        if not os.path.exists(file_url):
            raise HTTPException(status_code=404, detail=f"File not found: {file_url}")

        ext = Path(file_url).suffix.lower()

        # If the file is already viewable (PDF or image), just return it
        if ext in [".pdf", ".jpg", ".jpeg", ".png", ".tiff"]:
            return FileResponse(file_url, media_type="application/pdf", headers={"Content-Disposition": "inline"})

        # If it's a DOCX, MSG, or EML → Convert to PDF
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                output_pdf_path = tmp_pdf.name

            if ext == ".docx":
                # Convert DOCX → PDF using LibreOffice
                subprocess.run([
                    "soffice", "--headless", "--convert-to", "pdf", "--outdir",
                    os.path.dirname(output_pdf_path), file_url
                ], check=True)
                converted_file = Path(file_url).with_suffix(".pdf")
                if not converted_file.exists():
                    raise Exception("DOCX conversion failed")
                os.rename(str(converted_file), output_pdf_path)

            elif ext in [".msg", ".eml"]:
                # Convert email files using existing functions
                if ext == ".msg":
                    output_pdf_path = convert_msg_to_pdf(file_url)
                else:
                    output_pdf_path = convert_eml_to_pdf(file_url)

            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

            return FileResponse(output_pdf_path, media_type="application/pdf", headers={"Content-Disposition": "inline"})

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {e}")
    finally:
        db.close()


@router.get("/view_document_by_path")
def view_document_by_path(path: str = Query(...)):
    """View a document by its file path."""
    REQUEST_COUNT.labels(method='GET', endpoint='/view_document_by_path').inc()
    
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


@router.get("/get_sources/")
def get_sources():
    """Get available document sources."""
    REQUEST_COUNT.labels(method='GET', endpoint='/get_sources/').inc()
    
    db = sessionlocal()
    try:
        return get_source_options(db)
    finally:
        db.close()


@router.get("/download_and_view/{file_id}")
def download_and_view_document(file_id: int):
    """
    Download a document from Azure Blob Storage and view it.
    This endpoint downloads the file locally and serves it.
    """
    REQUEST_COUNT.labels(method='GET', endpoint='/download_and_view').inc()
    
    db = sessionlocal()
    try:
        doc = get_details_by_id(db, file_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        file_url = str(doc.file_url)
        
        # If it's an Azure Blob Storage URL, download it first
        if ".blob.core.windows.net" in file_url:
            try:
                # Download using the SAS URL directly
                temp_download_path = os.path.join(UPLOAD_DIR, f"temp_{uuid.uuid4()}")
                success = download_file_from_azure_blob(file_url, temp_download_path)
                
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to download file from Azure Blob Storage")
                
                file_url = temp_download_path
                logger.info(f"Downloaded blob to {temp_download_path}")
            
            except Exception as e:
                logger.error(f"Failed to download blob: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")
        
        # Now handle the local file
        if not os.path.exists(file_url):
            raise HTTPException(status_code=404, detail=f"File not found: {file_url}")

        ext = Path(file_url).suffix.lower()

        # If the file is already viewable (PDF or image), just return it
        if ext in [".pdf", ".jpg", ".jpeg", ".png", ".tiff"]:
            return FileResponse(file_url, media_type="application/pdf", headers={"Content-Disposition": "inline"})

        # If it's a DOCX, MSG, or EML → Convert to PDF
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                output_pdf_path = tmp_pdf.name

            if ext == ".docx":
                # Convert DOCX → PDF using LibreOffice
                subprocess.run([
                    "soffice", "--headless", "--convert-to", "pdf", "--outdir",
                    os.path.dirname(output_pdf_path), file_url
                ], check=True)
                converted_file = Path(file_url).with_suffix(".pdf")
                if not converted_file.exists():
                    raise Exception("DOCX conversion failed")
                os.rename(str(converted_file), output_pdf_path)

            elif ext in [".msg", ".eml"]:
                # Convert email files using existing functions
                if ext == ".msg":
                    output_pdf_path = convert_msg_to_pdf(file_url)
                else:
                    output_pdf_path = convert_eml_to_pdf(file_url)

            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

            return FileResponse(output_pdf_path, media_type="application/pdf", headers={"Content-Disposition": "inline"})

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {e}")
    
    finally:
        db.close()


