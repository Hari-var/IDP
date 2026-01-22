from datetime import datetime
from app.database.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime



class Document_logs(Base):
    __tablename__ = "document_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_name = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(255), nullable=False)
    doc_type_predicted = Column(String(255), nullable=False)
    processing_time_ms = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)
    file_url = Column(String(1024), nullable=False)


