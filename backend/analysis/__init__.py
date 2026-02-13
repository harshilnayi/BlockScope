"""
BlockScope Analysis Module.

Exports core components for smart contract vulnerability analysis.
"""

from .models import Finding as PydanticFinding
from .models import ScanRequest, ScanResult
from .orchestrator import AnalysisOrchestrator

# Also export the rule-based Finding for rule authors
try:
    from .rules.base import Finding as RuleFinding
    from .rules.base import Severity, VulnerabilityRule
except ImportError:
    pass

__all__ = [
    "AnalysisOrchestrator",
    "ScanRequest",
    "ScanResult",
    "PydanticFinding",
]
