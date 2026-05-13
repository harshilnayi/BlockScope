"""
SQLAlchemy ORM model for ``findings`` table.

Each ``Finding`` row belongs to a parent ``Scan`` and records a single
security finding detected in a smart contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.models.base import Base
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship


class Finding(Base):
    """
    Represents a single normalised vulnerability finding linked to a scan.

    The ``findings`` table complements the JSON ``findings`` column on the
    ``scans`` table, enabling structured queries (e.g., «all critical findings
    across all scans»).

    Attributes:
        id: Auto-generated primary key.
        scan_id: Foreign key referencing the parent ``Scan`` row.
        rule_id: Identifier of the detection rule that raised this finding.
        name: Short display name of the vulnerability.
        severity: Severity level (``critical``, ``high``, ``medium``, ``low``, ``info``).
        description: Full human-readable explanation of the vulnerability.
        line_number: Source-code line where the issue was detected.
        code_snippet: Relevant code excerpt for context.
        remediation: Suggested fix or mitigation strategy.
        confidence: Detection confidence score in [0, 1] (default 1.0).
        created_at: UTC timestamp of when the record was created.
        scan: ORM back-reference to the parent :class:`~app.models.scan.Scan`.
    """

    __tablename__ = "findings"
    __table_args__ = (
        # Composite index: efficiently query findings for a scan filtered by severity
        Index("idx_findings_scan_severity", "scan_id", "severity"),
    )

    # ──────────────────────────────────────────────
    # Columns
    # ──────────────────────────────────────────────
    id: int = Column(Integer, primary_key=True, index=True)
    scan_id: int = Column(
        Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )

    rule_id: str = Column(String(100), nullable=False, index=True)
    name: str = Column(String(255), nullable=False)
    severity: str = Column(String(20), nullable=False, index=True)
    description: str = Column(Text, nullable=False)
    line_number: Optional[int] = Column(Integer, nullable=True)
    code_snippet: Optional[str] = Column(Text, nullable=True)
    remediation: Optional[str] = Column(Text, nullable=True)
    confidence: float = Column(Float, default=1.0, nullable=False)

    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ──────────────────────────────────────────────
    # Relationships
    # ──────────────────────────────────────────────
    scan = relationship("Scan")

    # ──────────────────────────────────────────────
    # Dunder methods
    # ──────────────────────────────────────────────
    def __repr__(self) -> str:
        """Return debug-friendly string representation."""
        return (
            f"Finding(id={self.id}, scan_id={self.scan_id}, "
            f"severity={self.severity!r}, name={self.name!r})"
        )
