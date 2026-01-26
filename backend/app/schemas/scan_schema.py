"""Pydantic schemas for API request/response."""
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

class FindingResponse(BaseModel):
    """Finding response schema."""
    rule_id: str
    name: str
    severity: str
    description: str
    line_number: int
    code_snippet: str
    remediation: str
    confidence: float


class ScanRequest(BaseModel):
    """Scan request schema."""
    contract_name: str
    source_code: str


class ScanResponse(BaseModel):
    """Scan response schema."""
    scan_id: int
    contract_name: str
    vulnerabilities_count: int
    severity_breakdown: Dict[str, int]
    overall_score: float
    summary: str
    findings: List[FindingResponse] = []
    timestamp: datetime
class Config:
        from_attributes = True
        
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
