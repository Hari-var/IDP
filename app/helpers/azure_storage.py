"""
Azure Blob Storage utilities for document management
"""

import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, ContainerClient, generate_blob_sas, BlobSasPermissions
from app.helpers.logger import logger

# Try to use standard Azure SDK credentials first
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "idp-documents")

# Fallback to SAS URL configuration
SAS_URL = os.getenv("sas_url")
SAS_CONTAINER_NAME = os.getenv("container_name")

# Initialize Blob Service Client
blob_service_client = None
using_sas_url = False

try:
    if AZURE_STORAGE_CONNECTION_STRING:
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        logger.info("Azure Storage: Using connection string")
    elif AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY:
        blob_service_client = BlobServiceClient(
            account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=AZURE_STORAGE_ACCOUNT_KEY
        )
        logger.info("Azure Storage: Using account name and key")
    elif SAS_URL and SAS_CONTAINER_NAME:
        using_sas_url = True
        logger.info("Azure Storage: Using SAS URL (limited operations available)")
    else:
        logger.warning("Azure Storage credentials not configured - using SAS URL configuration if available")
except Exception as e:
    blob_service_client = None
    logger.error(f"Failed to initialize Azure Blob Service Client: {str(e)}")


def get_blob_service_client() -> BlobServiceClient:
    """Get the blob service client instance."""
    if not blob_service_client:
        raise Exception("Azure Blob Storage not configured. Check environment variables.")
    return blob_service_client


def get_container_client() -> ContainerClient:
    """Get the container client for the documents container."""
    return get_blob_service_client().get_container_client(AZURE_STORAGE_CONTAINER_NAME)


def ensure_container_exists() -> bool:
    """Ensure the container exists, create it if not."""
    try:
        container_client = get_blob_service_client().get_container_client(
            AZURE_STORAGE_CONTAINER_NAME
        )
        # Try to get container properties to check if it exists
        try:
            container_client.get_container_properties()
            return True
        except:
            # Container doesn't exist, create it
            created_container = get_blob_service_client().create_container(
                name=AZURE_STORAGE_CONTAINER_NAME
            )
            logger.info(f"Container '{AZURE_STORAGE_CONTAINER_NAME}' created successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to ensure container exists: {str(e)}")
        return False


def upload_file_to_blob(file_path: str, blob_name: str = None) -> str:
    """
    Upload a file to Azure Blob Storage and return the blob URL.
    
    Args:
        file_path: Local file path to upload
        blob_name: Name for the blob in storage (optional, defaults to filename)
    
    Returns:
        The SAS URL of the uploaded blob
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Use filename if blob_name not provided
        if not blob_name:
            blob_name = os.path.basename(file_path)
        
        # Add timestamp to ensure uniqueness
        file_ext = os.path.splitext(blob_name)[1]
        file_base = os.path.splitext(blob_name)[0]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"{file_base}_{timestamp}{file_ext}"
        
        # Ensure container exists
        ensure_container_exists()
        
        # Upload file
        container_client = get_container_client()
        with open(file_path, "rb") as file_data:
            container_client.upload_blob(
                name=blob_name,
                data=file_data,
                overwrite=True
            )
        
        logger.info(f"File uploaded to blob: {blob_name}")
        
        # Generate SAS URL for the blob
        blob_url = generate_blob_sas_url(blob_name)
        return blob_url
    
    except Exception as e:
        logger.error(f"Failed to upload file to blob storage: {str(e)}")
        raise


def generate_blob_sas_url(blob_name: str, expiry_hours: int = 24) -> str:
    """
    Generate a SAS URL for a blob with read permissions.
    
    Args:
        blob_name: Name of the blob
        expiry_hours: Number of hours the SAS URL is valid (default: 24)
    
    Returns:
        Full SAS URL for accessing the blob
    """
    try:
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=AZURE_STORAGE_ACCOUNT_NAME,
            container_name=AZURE_STORAGE_CONTAINER_NAME,
            blob_name=blob_name,
            account_key=AZURE_STORAGE_ACCOUNT_KEY,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        # Construct full URL
        blob_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER_NAME}/{blob_name}?{sas_token}"
        return blob_url
    
    except Exception as e:
        logger.error(f"Failed to generate SAS URL: {str(e)}")
        raise


def delete_blob(blob_name: str) -> bool:
    """
    Delete a blob from Azure Blob Storage.
    
    Args:
        blob_name: Name of the blob to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        container_client = get_container_client()
        container_client.delete_blob(blob_name)
        logger.info(f"Blob deleted: {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete blob: {str(e)}")
        return False


def list_blobs(prefix: str = None) -> list:
    """
    List blobs in the container.
    
    Args:
        prefix: Optional prefix to filter blobs
    
    Returns:
        List of blob names
    """
    try:
        container_client = get_container_client()
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]
    except Exception as e:
        logger.error(f"Failed to list blobs: {str(e)}")
        return []


def download_blob_to_file(blob_name: str, download_path: str) -> bool:
    """
    Download a blob from Azure Blob Storage to a local file.
    
    Args:
        blob_name: Name of the blob to download
        download_path: Local path to save the file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        container_client = get_container_client()
        blob_client = container_client.get_blob_client(blob_name)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        
        # Download blob
        with open(download_path, "wb") as file:
            download_stream = blob_client.download_blob()
            file.write(download_stream.readall())
        
        logger.info(f"Blob downloaded to: {download_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to download blob: {str(e)}")
        return False


def get_blob_properties(blob_name: str) -> dict:
    """
    Get properties of a blob.
    
    Args:
        blob_name: Name of the blob
    
    Returns:
        Dictionary containing blob properties
    """
    try:
        container_client = get_container_client()
        blob_client = container_client.get_blob_client(blob_name)
        properties = blob_client.get_blob_properties()
        
        return {
            "name": blob_name,
            "size": properties.size,
            "created": properties.creation_time,
            "modified": properties.last_modified,
            "content_type": properties.content_settings.content_type
        }
    except Exception as e:
        logger.error(f"Failed to get blob properties: {str(e)}")
        return {}
