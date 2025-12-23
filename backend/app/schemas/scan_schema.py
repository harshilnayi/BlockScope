"""Pydantic schemas for API request/response."""
from typing import List, Optional
from pydantic import BaseModel


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
    id: int
    contract_name: str
    status: str
    findings: List[FindingResponse] = []
    created_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
