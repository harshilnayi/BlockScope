"""Base class for vulnerability detection rules."""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Finding:
    """Represents a detected vulnerability finding."""
    rule_id: str
    name: str
    title: str
    name: str
    severity: Severity
    description: str
    line_number: int
    code_snippet: str
    remediation: str
    confidence: float = 1.0
    
    def __repr__(self) -> str:
        return f"{self.name} ({self.severity.value}) at line {self.line_number}"

class VulnerabilityRule:
    """Base class for all vulnerability detection rules."""
    
    def __init__(self, rule_id: str, name: str, severity: Severity):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
    
    def detect(self, ast) -> List[Finding]:
        """
        Detect vulnerabilities in AST.
        
        Args:
            ast: Abstract syntax tree from Slither
        
        Returns:
            List of Finding objects
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement detect()")
    
    def __repr__(self) -> str:
        return f"Rule({self.rule_id})"
