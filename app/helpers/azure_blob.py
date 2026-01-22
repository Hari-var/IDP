import os
import uuid
from datetime import datetime
from azure.storage.blob import BlobClient, ContentSettings 
from app.helpers.config import MY_SAS_URL, CONTAINER_NAME
from app.helpers.logger import logger


def upload_file_to_azure_blob(file_path: str, file_name: str = None) -> str:
    """
    Upload a file to Azure Blob Storage using SAS URL.
    
    Args:
        file_path: Local file path to upload
        file_name: Name for the blob (optional, defaults to filename)
    
    Returns:
        Full SAS URL for accessing the blob
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Use filename if file_name not provided
        if not file_name:
            file_name = os.path.basename(file_path)
        
        # Add timestamp to ensure uniqueness
        file_ext = os.path.splitext(file_name)[1]
        file_base = os.path.splitext(file_name)[0]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"{file_base}_{timestamp}{file_ext}"
        
        # Parse SAS URL
        if "?" not in MY_SAS_URL:
            raise ValueError("Invalid SAS URL - missing token")
        
        base_url, sas_token = MY_SAS_URL.split("?", 1)
        
        # Construct the full blob URL
        full_blob_url = f"{base_url.rstrip('/')}/{CONTAINER_NAME}/{blob_name}?{sas_token}"
        
        logger.info(f"Uploading file to Azure Blob: {blob_name}")
        
        # Create Blob Client
        blob_client = BlobClient.from_blob_url(blob_url=full_blob_url)
        
        # Upload file
        with open(file_path, "rb") as data:
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=get_content_type(file_name))
            )
        
        logger.info(f"✅ File uploaded to Azure Blob: {blob_name}")
        
        # Return the full SAS URL
        return full_blob_url
    
    except Exception as e:
        logger.error(f"Failed to upload file to Azure Blob: {str(e)}")
        raise


async def upload_stream_to_azure(file_stream, file_name, content_type):
    """
    Uploads a file stream directly to Azure without saving to disk first.
    """
    try:
        # Add timestamp to ensure uniqueness
        file_ext = os.path.splitext(file_name)[1]
        file_base = os.path.splitext(file_name)[0]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"{file_base}_{timestamp}{file_ext}"
        
        # 1. Parse SAS URL
        if "?" not in MY_SAS_URL:
            raise ValueError("Invalid SAS URL")
        
        base_url, sas_token = MY_SAS_URL.split("?", 1)
        
        # 2. Construct the full URL
        full_blob_url = f"{base_url.rstrip('/')}/{CONTAINER_NAME}/{blob_name}?{sas_token}"
        
        # 3. Create Blob Client
        blob_client = BlobClient.from_blob_url(blob_url=full_blob_url)
        
        logger.info(f"Uploading stream to Azure Blob: {blob_name}")

        # 4. Upload the stream directly
        blob_client.upload_blob(
            file_stream, 
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
        
        logger.info(f"✅ Stream uploaded to Azure Blob: {blob_name}")
        
        # Return the full SAS URL
        return full_blob_url
    
    except Exception as e:
        logger.error(f"Error uploading stream: {e}")
        raise


def get_content_type(file_name: str) -> str:
    """Get MIME type based on file extension."""
    ext = os.path.splitext(file_name)[1].lower()
    
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.msg': 'application/vnd.ms-outlook',
        '.eml': 'message/rfc822',
    }
    
    return mime_types.get(ext, 'application/octet-stream')


def download_file_from_azure_blob(sas_url: str, download_path: str) -> bool:
    """
    Download a file from Azure Blob Storage using SAS URL.
    
    Args:
        sas_url: Full SAS URL to the blob
        download_path: Local path to save the file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create blob client from SAS URL
        blob_client = BlobClient.from_blob_url(blob_url=sas_url)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        
        # Download blob
        with open(download_path, "wb") as file:
            download_stream = blob_client.download_blob()
            file.write(download_stream.readall())
        
        logger.info(f"✅ Downloaded blob to: {download_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to download blob from Azure: {str(e)}")
        return False

# def upload_to_azure(account_sas_url, container_name, local_file_path):
#     try:
#         file_name = os.path.basename(local_file_path)

#         if "?" not in account_sas_url:
#             raise ValueError("Your SAS URL is missing the token")
            
#         base_url, sas_token = account_sas_url.split("?", 1)
#         full_blob_url = f"{base_url.rstrip('/')}/{container_name}/{file_name}?{sas_token}"

#         print(f"Targeting: {base_url.rstrip('/')}/{container_name}/{file_name}")

#         blob_client = BlobClient.from_blob_url(blob_url=full_blob_url)
        
#         print("Uploading with Content-Type: image/jpg...")
        
#         with open(local_file_path, "rb") as data:
#             # 2. Pass content_settings inside the upload function
#             blob_client.upload_blob(
#                 data, 
#                 overwrite=True,
#                 content_settings=ContentSettings(content_type="image/jpg")
#             )
            
#         print("✅ Upload successful!")

#     except Exception as e:
#         print(f"❌ Error: {e}")

# # ================= CONFIGURATION =================

 
# LOCAL_FILE = r"C:\practice\RSS Feed\RSS_backend\img\pexels-cottonbro-6153354.jpg"

# upload_to_azure(MY_SAS_URL, CONTAINER_NAME, LOCAL_FILE)