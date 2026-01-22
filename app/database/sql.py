from app.database.database import sessionlocal, db_dependency
from app.database.model import Document_logs
from pydantic import BaseModel
from typing import Optional

class DocRequest(BaseModel):
    document_name: str
    source: str
    doc_type_predicted: str
    processing_time_ms: int
    summary: str
    file_url: str

class DocUpdateRequest(BaseModel):
    source: Optional[str] = None
    doc_type_predicted: Optional[str] = None
    summary: Optional[str] = None

def insert_document_log(db: db_dependency, doc: DocRequest):
    try:
        doc_data = Document_logs(**doc.model_dump())
        db.add(doc_data)
        db.commit()
        db.refresh(doc_data)
        return doc_data
    finally:
        db.close()

def get_document_by_id(db: db_dependency, doc_id: int):
    try:
        return db.query(Document_logs).filter(Document_logs.id == doc_id).first()
    finally:
        db.close()


def update_document_by_id(db : db_dependency,
    doc: DocUpdateRequest,
    doc_id: int
):
    try:
        existing_doc = db.query(Document_logs).filter(Document_logs.id == doc_id).first()
        if not existing_doc:
            return None

        doc_data = doc.model_dump(exclude_unset=True)

        for key, value in doc_data.items():
            setattr(existing_doc, key, value)

        db.commit()
        db.refresh(doc)
        return doc
    finally:
        db.close()


def delete_document_by_id(db: db_dependency, doc_id: int) -> bool:
    try:
        doc = db.query(Document_logs).filter(Document_logs.id == doc_id).first()
        if not doc:
            return False

        db.delete(doc)
        db.commit()
        return True
    finally:
        db.close()


def delete_all_document_logs(db: db_dependency):

    try:
        db.query(Document_logs).delete()
        db.commit()
    finally:
        db.close()

from sqlalchemy import func

def get_doc_type_count(db: db_dependency):
    try:
        return (
            db.query(
                Document_logs.doc_type_predicted,
                func.count(Document_logs.id).label("count")
            )
            .group_by(Document_logs.doc_type_predicted)
            .order_by(func.count(Document_logs.id).desc())
            .all()
        )
    finally:
        db.close()

def get_source_options(db: db_dependency):
    try:
        sources = (
            db.query(Document_logs.source)
            .distinct()
            .filter(Document_logs.source.isnot(None))
            .all()
        )

        # Convert list of tuples → list of strings
        return [s[0] for s in sources]
    finally:
        db.close()

def get_avg_processing_time(db: db_dependency):
    try:
        return (
            db.query(
                Document_logs.doc_type_predicted,
                func.avg(Document_logs.processing_time_ms).label("avg_time")
            )
            .group_by(Document_logs.doc_type_predicted)
            .order_by(Document_logs.doc_type_predicted.asc())
            .all()
        )
    finally:
        db.close()


def get_recent_documents(
    db: db_dependency,
    selected_source=None,
    selected_doc_type=None,
    date_range=None,
    file_name_input=None,
    page_num=1,
    page_size=10
):
    try:
        query = db.query(Document_logs)

        if selected_source and selected_source != "All":
            query = query.filter(Document_logs.source == selected_source)

        if selected_doc_type and selected_doc_type != "All":
            query = query.filter(Document_logs.doc_type_predicted == selected_doc_type)

        if date_range and len(date_range) == 2:
            query = query.filter(
                Document_logs.timestamp.between(date_range[0], date_range[1])
            )

        if file_name_input:
            query = query.filter(
                Document_logs.document_name.ilike(f"%{file_name_input}%")
            )

        return (
            query
            .order_by(Document_logs.timestamp.desc())
            .offset((page_num - 1) * page_size)
            .limit(page_size)
            .all()
        )
    finally:
        db.close()


def get_details_by_id(db: db_dependency, doc_id: int):
    try:
        return db.query(Document_logs).filter(Document_logs.id == doc_id).first()
    finally:
        db.close()
