from fastapi import APIRouter

from app.database.database import sessionlocal
from app.database.sql import (
    get_doc_type_count,
    get_avg_processing_time,
    delete_document_by_id
)

router = APIRouter(prefix="/crud_ops", tags=["CRUD Operations"])


@router.get("/get_doc_types/")
async def get_doc_types():
    """
    Endpoint to retrieve document types.
    """
    db = sessionlocal()
    try:
        results = get_doc_type_count(db)
        return [
            {
                "doc_type_predicted": doc_type,
                "count": count
            }
            for doc_type, count in results
        ]
    finally:
        db.close()


@router.get("/get_avg_processing_time/")
async def get_average_processing_time():
    """
    Endpoint to retrieve average processing time by document type.
    """
    db = sessionlocal()
    try:
        results = get_avg_processing_time(db)
        return [
            {
                "doc_type": doc_type,
                "avg_processing_time": avg_time
            }
            for doc_type, avg_time in results
        ]
    finally:
        db.close()


@router.delete("/delete_document_by_id/{file_id}")
def process_delete_document_by_id(file_id: int):
    """
    Endpoint to delete a document by its ID.
    """
    db = sessionlocal()
    try:
        result = delete_document_by_id(db, file_id)
        if result:
            return {"message": "Document deleted successfully."}
        return {"message": "Failed to delete document."}
    finally:
        db.close()