"""
Analysis module exports.

This module provides the core analysis components for smart contract security scanning:
- AnalysisOrchestrator: Coordinates all vulnerability detection tools
- ScanRequest: Input model for analysis requests
- ScanResult: Output model containing findings and scores

Usage:
    from analysis import AnalysisOrchestrator, ScanRequest, ScanResult
    
    orchestrator = AnalysisOrchestrator(rules=[...])
    result = orchestrator.analyze(ScanRequest(source_code=contract_code))
"""

from analysis.orchestrator import AnalysisOrchestrator
from analysis.models import ScanRequest, ScanResult, Finding

__all__ = [
    "AnalysisOrchestrator",
    "ScanRequest", 
    "ScanResult",
    "Finding"
]

# Version info
__version__ = "1.0.0"
__author__ = "BlockScope Team"
