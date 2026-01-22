"""
Document Viewer Router - Provides embedded viewing via iframes
Supports Azure Blob Storage URLs and local files
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from app.database.database import sessionlocal
from app.database.sql import get_details_by_id
from app.helpers.logger import logger

router = APIRouter(prefix="/viewer", tags=["Document Viewer"])


def get_embed_url(file_url: str) -> str:
    """
    Convert file URL to embeddable format.
    For PDFs: Direct URL or data URL
    For other formats: Convert to base64 or use conversion service
    """
    if ".blob.core.windows.net" in file_url:
        # Azure Blob Storage URL - directly embeddable
        return file_url
    elif file_url.endswith(".pdf"):
        # Local PDF - serve directly
        return f"/viewer/file?path={file_url}"
    else:
        # Other formats - may need conversion
        return f"/viewer/convert?path={file_url}"


@router.get("/document/{file_id}", response_class=HTMLResponse)
def view_document_embedded(file_id: int, embed_mode: str = "iframe"):
    """
    View document in embedded viewer (no download required).
    
    Parameters:
    - file_id: Document ID
    - embed_mode: 'iframe' (default), 'object', or 'embed'
    
    Returns: HTML page with embedded viewer
    """
    db = sessionlocal()
    try:
        doc = get_details_by_id(db, file_id)
        if not doc:
            return generate_error_page(404, "Document not found")

        file_url = str(doc.file_url)
        file_name = str(doc.document_name)
        
        # Determine if file can be embedded directly
        is_azure = ".blob.core.windows.net" in file_url
        is_pdf = file_url.lower().endswith(".pdf") or ".pdf" in file_url
        
        logger.info(f"Embedding document {file_id}: Azure={is_azure}, PDF={is_pdf}")
        
        # Generate appropriate HTML based on file type
        if is_pdf or is_azure:
            html = generate_pdf_viewer(file_url, file_name, embed_mode)
        else:
            html = generate_conversion_notice(file_id, file_name)
        
        return html
    
    finally:
        db.close()


@router.get("/frame/{file_id}", response_class=HTMLResponse)
def view_document_frame(file_id: int):
    """
    Minimal iframe viewer - just the document in a frame.
    Perfect for embedding in other applications.
    """
    db = sessionlocal()
    try:
        doc = get_details_by_id(db, file_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        file_url = str(doc.file_url)
        doc_name = str(doc.document_name)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{doc_name}</title>
            <style>
                body {{ margin: 0; padding: 0; }}
                iframe {{ width: 100%; height: 100vh; border: none; }}
            </style>
        </head>
        <body>
            <iframe src="{file_url}" style="width: 100%; height: 100vh;"></iframe>
        </body>
        </html>
        """
        return html
    
    finally:
        db.close()


@router.get("/fullscreen/{file_id}", response_class=HTMLResponse)
def view_document_fullscreen(file_id: int):
    """
    Fullscreen document viewer with toolbar and controls.
    """
    db = sessionlocal()
    try:
        doc = get_details_by_id(db, file_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        file_url = str(doc.file_url)
        doc_name = str(doc.document_name)
        doc_type = str(doc.doc_type_predicted)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{doc_name}</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: #f5f5f5;
                }}
                .toolbar {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 16px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .toolbar-left {{
                    display: flex;
                    gap: 20px;
                    align-items: center;
                }}
                .toolbar-title {{
                    font-size: 18px;
                    font-weight: 600;
                }}
                .toolbar-info {{
                    font-size: 13px;
                    opacity: 0.9;
                    display: flex;
                    gap: 15px;
                }}
                .info-item {{
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }}
                .toolbar-right {{
                    display: flex;
                    gap: 10px;
                }}
                button {{
                    background: rgba(255,255,255,0.2);
                    border: 1px solid rgba(255,255,255,0.3);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 13px;
                    transition: all 0.3s;
                }}
                button:hover {{
                    background: rgba(255,255,255,0.3);
                    border-color: rgba(255,255,255,0.5);
                }}
                .viewer-container {{
                    width: 100%;
                    height: calc(100vh - 60px);
                    overflow: auto;
                    background: white;
                }}
                iframe {{
                    width: 100%;
                    height: 100%;
                    border: none;
                }}
                .status-bar {{
                    background: #f9f9f9;
                    padding: 8px 20px;
                    font-size: 12px;
                    color: #666;
                    border-top: 1px solid #e0e0e0;
                }}
            </style>
        </head>
        <body>
            <div class="toolbar">
                <div class="toolbar-left">
                    <div class="toolbar-title">📄 {doc_name}</div>
                    <div class="toolbar-info">
                        <div class="info-item">
                            <span>Type:</span> <strong>{doc_type}</strong>
                        </div>
                    </div>
                </div>
                <div class="toolbar-right">
                    <button onclick="downloadFile()">⬇️ Download</button>
                    <button onclick="printFile()">🖨️ Print</button>
                    <button onclick="fullscreenToggle()">⛶ Fullscreen</button>
                </div>
            </div>
            
            <div class="viewer-container">
                <iframe id="docFrame" src="{file_url}"></iframe>
            </div>
            
            <div class="status-bar">
                <span>Document loaded from Azure Blob Storage • Secure access via SAS URL</span>
            </div>
            
            <script>
                function downloadFile() {{
                    window.location.href = "/document_data/download_and_view/{file_id}";
                }}
                
                function printFile() {{
                    const frame = document.getElementById('docFrame');
                    frame.contentWindow.print();
                }}
                
                function fullscreenToggle() {{
                    const frame = document.getElementById('docFrame');
                    if (frame.requestFullscreen) {{
                        frame.requestFullscreen();
                    }}
                }}
            </script>
        </body>
        </html>
        """
        return html
    
    finally:
        db.close()


def generate_pdf_viewer(file_url: str, file_name: str, embed_mode: str = "iframe") -> str:
    """Generate HTML for PDF viewer using PDF.js (embedded, no download)."""
    
    pdf_js_url = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"
    pdf_worker_url = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{file_name}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: #272726;
            }}
            .container {{ 
                display: flex; 
                height: 100vh; 
            }}
            .toolbar {{
                background: #323232;
                color: white;
                padding: 12px 20px;
                display: flex;
                align-items: center;
                gap: 15px;
                flex-wrap: wrap;
                border-bottom: 1px solid #444;
            }}
            .toolbar-item {{ display: flex; align-items: center; gap: 10px; }}
            button {{
                background: #555;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.3s;
            }}
            button:hover {{ background: #666; }}
            button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
            input[type="number"] {{
                width: 60px;
                padding: 6px;
                border: 1px solid #666;
                border-radius: 3px;
                background: #444;
                color: white;
            }}
            .pdf-container {{
                flex: 1;
                overflow: auto;
                display: flex;
                justify-content: center;
                background: #272726;
            }}
            canvas {{
                max-width: 100%;
                height: auto;
                box-shadow: 0 0 20px rgba(0,0,0,0.3);
                margin: 20px auto;
            }}
            .info-bar {{
                background: #1a1a1a;
                color: #ccc;
                padding: 10px 20px;
                text-align: center;
                font-size: 12px;
                border-top: 1px solid #444;
            }}
        </style>
    </head>
    <body>
        <div class="toolbar">
            <button onclick="prevPage()">← Previous</button>
            <div class="toolbar-item">
                <span>Page</span>
                <input type="number" id="pageNum" value="1" min="1" onchange="goToPage(this.value)">
                <span>of <span id="pageCount">0</span></span>
            </div>
            <button onclick="nextPage()">Next →</button>
            <span style="margin-left: auto;">📄 {file_name}</span>
        </div>
        
        <div class="pdf-container">
            <canvas id="canvas"></canvas>
        </div>
        
        <div class="info-bar">
            ✓ Document loaded from Azure Blob Storage • View without download • Secure SAS URL
        </div>

        <script src="{pdf_js_url}"></script>
        <script>
            pdfjsLib.GlobalWorkerOptions.workerSrc = '{pdf_worker_url}';
            
            const pdfUrl = '{file_url}';
            let pdfDoc = null;
            let pageNum = 1;
            let pageRendering = false;
            let pageNumPending = null;
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            
            // Load PDF
            pdfjsLib.getDocument(pdfUrl).promise.then(function(pdf) {{
                pdfDoc = pdf;
                document.getElementById('pageCount').textContent = pdf.numPages;
                renderPage(pageNum);
            }}).catch(function(error) {{
                console.error('Error loading PDF:', error);
                document.body.innerHTML = '<div style="color: white; padding: 20px;">Error loading document: ' + error.message + '</div>';
            }});
            
            function renderPage(num) {{
                if (pageRendering) {{
                    pageNumPending = num;
                    return;
                }}
                pageRendering = true;
                pdfDoc.getPage(num).then(function(page) {{
                    const viewport = page.getViewport({{scale: 2}});
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;
                    
                    const renderContext = {{
                        canvasContext: ctx,
                        viewport: viewport
                    }};
                    
                    page.render(renderContext).promise.then(function() {{
                        pageRendering = false;
                        if (pageNumPending !== null) {{
                            renderPage(pageNumPending);
                            pageNumPending = null;
                        }}
                    }});
                }});
                
                document.getElementById('pageNum').value = num;
            }}
            
            function prevPage() {{
                if (pageNum <= 1) return;
                pageNum--;
                renderPage(pageNum);
            }}
            
            function nextPage() {{
                if (pageNum >= pdfDoc.numPages) return;
                pageNum++;
                renderPage(pageNum);
            }}
            
            function goToPage(num) {{
                num = parseInt(num);
                if (num < 1 || num > pdfDoc.numPages) return;
                pageNum = num;
                renderPage(pageNum);
            }}
            
            // Keyboard navigation
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'ArrowLeft') prevPage();
                if (e.key === 'ArrowRight') nextPage();
            }});
        </script>
    </body>
    </html>
    """
    return html


def generate_conversion_notice(file_id: int, file_name: str) -> str:
    """Generate HTML for file conversion notice."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document Viewer</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                padding: 40px;
                max-width: 500px;
                text-align: center;
            }}
            .icon {{ font-size: 64px; margin-bottom: 20px; }}
            h1 {{ color: #333; margin: 20px 0; }}
            p {{ color: #666; line-height: 1.6; margin: 15px 0; }}
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                border-radius: 6px;
                text-decoration: none;
                margin-top: 20px;
                border: none;
                cursor: pointer;
                font-size: 16px;
                transition: transform 0.3s;
            }}
            .btn:hover {{ transform: translateY(-2px); }}
            .info {{
                background: #f0f4ff;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                font-size: 14px;
                color: #555;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">🔄</div>
            <h1>Document Conversion Required</h1>
            <p>The file <strong>{file_name}</strong> needs to be converted to PDF for viewing.</p>
            <p>Click the button below to download and view the document.</p>
            
            <button class="btn" onclick="window.location.href='/document_data/download_and_view/{file_id}'">
                ⬇️ Download & View Document
            </button>
            
            <div class="info">
                ℹ️ This document will be converted to PDF format and displayed in your browser.
            </div>
        </div>
    </body>
    </html>
    """
    return html


def generate_error_page(status_code: int, message: str) -> str:
    """Generate HTML error page."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Error {status_code}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                padding: 40px;
                max-width: 500px;
                text-align: center;
            }}
            .error-code {{ font-size: 72px; color: #f5576c; font-weight: bold; }}
            h1 {{ color: #333; margin: 20px 0; }}
            p {{ color: #666; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-code">{status_code}</div>
            <h1>Error</h1>
            <p>{message}</p>
        </div>
    </body>
    </html>
    """
    return html
