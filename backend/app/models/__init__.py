"""
SQLAlchemy model registry for BlockScope.

All models must be imported here so SQLAlchemy can resolve
ORM relationships before any engine creates tables.
Import order matters: Finding must be imported before Scan
because Scan.finding_records references Finding by name.
"""

from app.models.finding import Finding
from app.models.scan import Scan

__all__ = ["Finding", "Scan"]
