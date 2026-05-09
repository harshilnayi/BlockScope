"""
SQLAlchemy model registry for BlockScope.

All models must be imported here so SQLAlchemy can resolve
ORM relationships before any engine creates tables.
Import order matters: Scan must be imported before Finding
because Finding.scan = relationship("Scan") resolves "Scan"
by string name at mapper configuration time — the Scan class
must already be registered in SQLAlchemy's mapper registry
before Finding is configured, otherwise mapper init raises
InvalidRequestError: 'Scan' failed to locate a name.
"""

from app.models.scan import Scan
from app.models.finding import Finding

__all__ = ["Scan", "Finding"]