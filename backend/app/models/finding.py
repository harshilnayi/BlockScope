"""Database model for findings."""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from backend.app.models.base import Base


class Finding(Base):
    """Finding / vulnerability database model."""
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)

    rule_id = Column(String, nullable=False)
    name = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    line_number = Column(Integer, nullable=False)
    code_snippet = Column(Text, nullable=False)
    remediation = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)

    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="findings")
