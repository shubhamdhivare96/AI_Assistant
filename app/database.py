from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from app.config import get_settings

settings = get_settings()

# Use SQLite for local persistence
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL if hasattr(settings, 'DATABASE_URL') else "sqlite:///./ai_assistant.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
