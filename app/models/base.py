"""
Base model and common functionality
NOTE: SQLAlchemy models kept for future database integration
Currently not used (system uses in-memory storage)
"""
from datetime import datetime
from typing import Optional

# SQLAlchemy imports commented out - not currently used
# from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
# from sqlalchemy import DateTime, func

# Base class for future database models
# class Base(DeclarativeBase):
#     """Base class for all database models"""
#     pass

# Common mixin for timestamp fields
class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    
    # created_at: Mapped[datetime] = mapped_column(
    #     DateTime(timezone=True),
    #     server_default=func.now(),
    #     nullable=False
    # )
    
    # updated_at: Mapped[datetime] = mapped_column(
    #     DateTime(timezone=True),
    #     server_default=func.now(),
    #     onupdate=func.now(),
    #     nullable=False
    # )
    
    def __init__(self):
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
