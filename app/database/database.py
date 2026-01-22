from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from fastapi import Depends #type: ignore
from typing import Annotated
from sqlalchemy.orm import Session
# import database.model as model
from app.helpers.config import cloud_db


engine = create_engine(
    cloud_db,
    echo=True
)

sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
