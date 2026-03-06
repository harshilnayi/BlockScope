"""
Pydantic schemas for scan API requests and responses.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class ScanRequest(BaseModel):
    """Schema for scan request body."""

    source_code: str
    contract_name: Optional[str] = None


class FindingResponse(BaseModel):
    """Schema for a single finding in the response."""

    title: str
    description: str
    severity: str
    line_number: Optional[int] = None


class ScanResponse(BaseModel):
    """Schema for scan response — matches what routers/scan.py returns."""

    scan_id: int
    contract_name: str
    vulnerabilities_count: int
    severity_breakdown: Dict[str, int]
    overall_score: int
    summary: str
    findings: List[FindingResponse] = []
    timestamp: datetime
