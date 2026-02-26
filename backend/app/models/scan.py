"""
SQLAlchemy models for scan data.

Defines the Scan and Finding tables.
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class Scan(Base):
    """Represents a smart contract scan result."""

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    contract_name = Column(String(255), nullable=False)
    source_code = Column(Text, nullable=False)
    status = Column(String(50), default="completed")

    # Analysis results
    vulnerabilities_count = Column(Integer, default=0)
    severity_breakdown = Column(JSON, nullable=True)
    overall_score = Column(Integer, default=100)
    summary = Column(Text, nullable=True)
    findings = Column(JSON, nullable=True)  # JSON list of finding dicts

    # Timestamps
    scanned_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to structured finding records (for normalized queries)
    finding_records = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")


class Finding(Base):
    """Represents an individual vulnerability finding."""

    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    title = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)
    description = Column(Text)
    line_number = Column(Integer, nullable=True)
    code_snippet = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="finding_records")
