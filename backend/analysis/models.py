"""
Data models for smart contract security scanning.

This module defines the core data structures used for scan requests and results.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """
    Represents a single security finding/vulnerability in a smart contract.
    """

    title: str = Field(..., description="Short title of the vulnerability")
    severity: str = Field(..., description="Severity level: critical, high, medium, low, or info")
    description: str = Field(..., description="Detailed description of the vulnerability")
    line_number: Optional[int] = Field(None, description="Line number where the issue was found")
    code_snippet: Optional[str] = Field(None, description="Relevant code snippet")
    recommendation: Optional[str] = Field(None, description="Suggested fix or mitigation")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Reentrancy Vulnerability",
                "severity": "critical",
                "description": "Function is vulnerable to reentrancy attacks",
                "line_number": 42,
                "code_snippet": "balance[msg.sender] -= amount;",
                "recommendation": "Use the checks-effects-interactions pattern",
            }
        }


class ScanRequest(BaseModel):
    """
    Request model for initiating a smart contract security scan.
    """

    source_code: str = Field(..., description="The Solidity contract source code to scan")
    contract_name: Optional[str] = Field(
        None, description="Name of the contract. Auto-detected if not provided"
    )
    file_path: str = Field(
        ..., description="Path or identifier for the file being scanned, used for logging"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_code": "pragma solidity ^0.8.0;\ncontract MyToken { ... }",
                "contract_name": "MyToken",
                "file_path": "/contracts/MyToken.sol",
            }
        }


class ScanResult(BaseModel):
    """
    Complete result of a smart contract security scan.
    """

    contract_name: str = Field(..., description="Name of the scanned contract")
    source_code: str = Field(..., description="Full source code of the contract for reference")
    findings: List[Finding] = Field(
        default_factory=list, description="List of all security findings"
    )
    vulnerabilities_count: int = Field(
        ..., description="Total number of findings/vulnerabilities detected"
    )
    severity_breakdown: Dict[str, int] = Field(
        ..., description="Count of findings by severity level (critical, high, medium, low, info)"
    )
    overall_score: int = Field(
        ..., ge=0, le=100, description="Security score from 0-100, where 100 is safest"
    )
    summary: str = Field(
        ..., description="One-line summary of scan results (e.g., '2 critical, 1 high - UNSAFE')"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="UTC timestamp when the scan was completed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "contract_name": "MyToken",
                "source_code": "pragma solidity ^0.8.0;\ncontract MyToken { ... }",
                "findings": [
                    {
                        "title": "Reentrancy Vulnerability",
                        "severity": "critical",
                        "description": "Function is vulnerable to reentrancy attacks",
                        "line_number": 42,
                        "code_snippet": "balance[msg.sender] -= amount;",
                        "recommendation": "Use the checks-effects-interactions pattern",
                    }
                ],
                "vulnerabilities_count": 3,
                "severity_breakdown": {"critical": 2, "high": 1, "medium": 0, "low": 0, "info": 0},
                "overall_score": 35,
                "summary": "2 critical, 1 high - UNSAFE",
                "timestamp": "2024-12-24T10:30:00Z",
            }
        }
