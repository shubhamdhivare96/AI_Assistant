"""
Database configuration and session management
NOTE: PostgreSQL removed - using in-memory storage only
This file is kept for reference but all functionality is commented out
"""

# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker, Session
# from sqlalchemy.orm import sessionmaker, scoped_session
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.pool import QueuePool
# from contextlib import contextmanager
# from typing import Generator
# import logging

# from app.config import get_settings

# settings = get_settings()

# # Create SQLAlchemy engine
# engine = create_engine(
#     settings.DATABASE_URL,
#     echo=settings.DATABASE_ECHO,
#     pool_size=settings.DATABASE_POOL_SIZE,
#     max_overflow=settings.DATABASE_MAX_OVERFLOW,
#     pool_pre_ping=True,
#     pool_recycle=settings.DATABASE_POOL_RECYCLE,
#     pool_pre_ping=True,
#     pool_use_lifo=True,
#     pool_pre_ping=True,
#     pool_recycle=3600,
#     pool_size=20,
#     max_overflow=20,
#     pool_timeout=30,
#     pool_recycle=3600,
#     pool_pre_ping=True
# )

# # Create session factory
# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine,
#     expire_on_commit=False
# )

# # Scoped session for thread safety
# SessionLocal = scoped_session(SessionLocal)

# # Base class for models
# Base = declarative_base()

# def get_db() -> Session:
#     """
#     Get database session
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# @contextmanager
# def get_db_session() -> Session:
#     """
#     Context manager for database session
#     """
#     db = SessionLocal()
#     try:
#         yield db
#         db.commit()
#     except Exception as e:
#         db.rollback()
#         raise
#     finally:
#         db.close()

# def get_db_session() -> Session:
#     """
#     Get database session (for use in FastAPI dependencies)
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# def init_db():
#     """
#     Initialize database (create tables)
#     """
#     from app.models import Base
#     Base.metadata.create_all(bind=engine)
#     logging.info("Database tables created")

# def get_db_connection():
#     """
#     Get database connection
#     """
#     return engine.connect()

# def get_db_engine():
#     """
#     Get database engine
#     """
#     return engine

# # Create all tables on startup
# def create_tables():
#     """
#     Create all tables
#     """
#     Base.metadata.create_all(bind=engine)
#     logging.info("Database tables created")

# # Dependency to get DB session
# def get_db():
#     """
#     Dependency to get database session
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
