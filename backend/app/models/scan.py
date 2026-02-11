"""Database models for scans and findings."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from backend.app.models.base import Base

class Scan(Base):
    """Scan database model."""
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_name = Column(String, nullable=False)
    source_code = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    overall_score = Column(Float, nullable=False)   # ✅ ADD
    summary = Column(Text, nullable=False) 
    vulnerabilities_count = Column(Integer, nullable=False)
    severity_breakdown = Column(JSON, nullable=False)
    scanned_at = Column(DateTime, nullable=False)
    
    # Relationships
    findings = relationship(
         "Finding", 
         back_populates="scan",
         cascade="all, delete-orphan",
)
