import tempfile
import subprocess
import os
import extract_msg
from pathlib import Path
import fitz  # PyMuPDF
from email.parser import BytesParser
from email import policy

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