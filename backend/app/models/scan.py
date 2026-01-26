"""Database models for scans and findings."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy import JSON

class Scan(Base):
    """Scan database model."""
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_name = Column(String(255), nullable=False)
    source_code = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    overall_score = Column(Float, nullable=False)   # ✅ ADD
    summary = Column(Text, nullable=False) 
    vulnerabilities_count = Column(Integer, nullable=False)
    severity_breakdown = Column(JSON, nullable=False)
    findings = Column(JSON, nullable=False, default=list)   # IMPORTANT
    scanned_at = Column(DateTime, nullable=False)
    
    # Relationships
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")


class Finding(Base):
    """Finding/vulnerability database model."""
    __tablename__ = "findings"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    rule_id = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)  # critical, high, medium, low
    description = Column(Text, nullable=False)
    line_number = Column(Integer, nullable=False)
    code_snippet = Column(Text, nullable=False)
    remediation = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scan = relationship("Scan", back_populates="findings")
