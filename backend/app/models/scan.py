"""
SQLAlchemy models for scan data.

Defines the Scan and Finding tables.
"""

from datetime import datetime, timezone

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class Scan(Base):
    """Represents a smart contract scan result."""

    __tablename__ = "scans"
    __table_args__ = {"extend_existing": True}

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
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to structured finding records (for normalized queries)
    finding_records = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
