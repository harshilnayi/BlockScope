"""
Analysis Orchestrator - Coordinates all vulnerability detection tools.

This module orchestrates the complete security analysis pipeline:
1. Runs Slither static analysis via SlitherWrapper
2. Executes custom vulnerability detection rules
3. Aggregates and deduplicates findings
4. Calculates security scores
5. Returns comprehensive scan results
"""

from typing import List, Dict, Tuple
from pathlib import Path
import tempfile
import os
from datetime import datetime
import sys

# Add backend to path if needed
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import with absolute paths from backend root
from analysis.models import ScanRequest, ScanResult, Finding as PydanticFinding
from analysis.rules.base import VulnerabilityRule, Finding as RuleFinding
from analysis.slither_wrapper import SlitherWrapper


class AnalysisOrchestrator:
    """
    Orchestrates the complete smart contract security analysis pipeline.
    
    This class coordinates multiple analysis tools and aggregates their findings
    into a unified security report with calculated risk scores.
    """
    
    def __init__(self, rules: List[VulnerabilityRule]):
        """
        Initialize the orchestrator with vulnerability detection rules.
        
        Args:
            rules: List of VulnerabilityRule instances to run during analysis
        """
        self.rules = rules
        self.slither_wrapper = SlitherWrapper()
    
    def analyze(self, request: ScanRequest) -> ScanResult:
        """
        Perform complete security analysis on a smart contract.
        
        This method:
        1. Runs Slither static analysis
        2. Executes all registered vulnerability rules
        3. Deduplicates findings
        4. Calculates security score
        5. Returns comprehensive results
        
        Args:
            request: ScanRequest containing source code and metadata
            
        Returns:
            ScanResult with all findings, scores, and summary
        """
        print(f"🔍 Starting analysis for: {request.file_path}")
        
        # Step 1: Run Slither analysis
        slither_findings = self._run_slither_analysis(request)
        print(f"   ✓ Slither found {len(slither_findings)} issues")
        
        # Step 2: Run custom vulnerability rules
        rule_findings = self._run_rule_analysis(request)
        print(f"   ✓ Rules found {len(rule_findings)} issues")
        
        # Step 3: Merge and deduplicate findings
        all_findings = self._merge_and_deduplicate(slither_findings, rule_findings)
        print(f"   ✓ Total unique findings: {len(all_findings)}")
        
        # Step 4: Calculate severity breakdown
        severity_breakdown = self._calculate_severity_breakdown(all_findings)
        
        # Step 5: Calculate overall security score
        overall_score = self._calculate_score(all_findings)
        
        # Step 6: Generate summary
        summary = self._generate_summary(severity_breakdown, overall_score)
        
        # Step 7: Extract or detect contract name
        contract_name = request.contract_name or self._extract_contract_name(request.source_code)
        
        # Step 8: Build and return ScanResult
        result = ScanResult(
            contract_name=contract_name,
            source_code=request.source_code,
            findings=all_findings,
            vulnerabilities_count=len(all_findings),
            severity_breakdown=severity_breakdown,
            overall_score=overall_score,
            summary=summary,
            timestamp=datetime.utcnow()
        )
        
        print(f"✅ Analysis complete: {summary}")
        return result
    
    def _run_slither_analysis(self, request: ScanRequest) -> List[PydanticFinding]:
        """
        Run Slither static analysis on the contract.
        
        Args:
            request: ScanRequest with source code
            
        Returns:
            List of Pydantic Finding objects from Slither
        """
        findings = []
        
        # Check if Slither is available
        if not self.slither_wrapper.available:
            print("   ⚠️  Slither not available, skipping static analysis")
            return findings
        
        # Create temporary file for Slither analysis
        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.sol',
                delete=False,
                encoding='utf-8'
            ) as tmp_file:
                tmp_file.write(request.source_code)
                tmp_file_path = str(Path(tmp_file.name).resolve())
            
            # Run Slither
            slither_obj = self.slither_wrapper.parse_contract(tmp_file_path)
            
            # Extract findings from Slither
            if slither_obj and hasattr(slither_obj, 'detectors_results'):
                for detector_result in slither_obj.detectors_results:
                    finding = self._convert_slither_finding(detector_result)
                    if finding:
                        findings.append(finding)
            
        except Exception as e:
            print(f"   ⚠️  Slither analysis failed: {e}")
        finally:
            # Clean up temporary file
            try:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            except:
                pass
        
        return findings
    
    def _run_rule_analysis(self, request: ScanRequest) -> List[PydanticFinding]:
        """
        Run all registered vulnerability detection rules.
        
        Args:
            request: ScanRequest with source code
            
        Returns:
            List of Pydantic Finding objects from rules
        """
        findings = []
        
        # Create temporary file for rule analysis
        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.sol',
                delete=False,
                encoding='utf-8'
            ) as tmp_file:
                tmp_file.write(request.source_code)
                tmp_file_path = str(Path(tmp_file.name).resolve())
            
            # Parse contract for rules (if Slither available)
            ast = None
            if self.slither_wrapper.available:
                try:
                    slither_obj = self.slither_wrapper.parse_contract(tmp_file_path)
                    ast = self.slither_wrapper.get_ast_nodes(slither_obj)
                except Exception as e:
                    print(f"   ⚠️  AST parsing failed: {e}")
            
            # Run each rule
            for rule in self.rules:
                try:
                    rule_findings = rule.detect(ast) if ast else []
                    
                    # Convert RuleFinding to PydanticFinding
                    for rf in rule_findings:
                        pydantic_finding = self._convert_rule_finding(rf)
                        findings.append(pydantic_finding)
                        
                except Exception as e:
                    print(f"   ⚠️  Rule {rule.rule_id} failed: {e}")
                    
        except Exception as e:
            print(f"   ⚠️  Rule analysis setup failed: {e}")
        finally:
            # Clean up temporary file
            try:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            except:
                pass
        
        return findings
    
    def _convert_slither_finding(self, detector_result: Dict) -> PydanticFinding:
        """
        Convert Slither detector result to Pydantic Finding.
        
        Args:
            detector_result: Raw detector result from Slither
            
        Returns:
            PydanticFinding object
        """
        # Map Slither impact to severity
        impact_map = {
            'High': 'critical',
            'Medium': 'high',
            'Low': 'medium',
            'Informational': 'low'
        }
        
        severity = impact_map.get(
            detector_result.get('impact', 'Low'),
            'low'
        )
        
        # Extract line number from elements if available
        line_number = None
        code_snippet = None
        if 'elements' in detector_result and detector_result['elements']:
            first_element = detector_result['elements'][0]
            if 'source_mapping' in first_element:
                line_number = first_element['source_mapping'].get('lines', [None])[0]
        
        return PydanticFinding(
            title=detector_result.get('check', 'Unknown Slither Issue'),
            severity=severity,
            description=detector_result.get('description', 'Issue detected by Slither'),
            line_number=line_number,
            code_snippet=code_snippet,
            recommendation=detector_result.get('recommendation', 'Review Slither documentation')
        )
    
    def _convert_rule_finding(self, rule_finding: RuleFinding) -> PydanticFinding:
        """
        Convert RuleFinding (dataclass) to PydanticFinding.
        
        Args:
            rule_finding: RuleFinding from vulnerability rule
            
        Returns:
            PydanticFinding object
        """
        return PydanticFinding(
            title=rule_finding.name,
            severity=rule_finding.severity.value,
            description=rule_finding.description,
            line_number=rule_finding.line_number,
            code_snippet=rule_finding.code_snippet,
            recommendation=rule_finding.remediation
        )
    
    def _merge_and_deduplicate(
        self,
        slither_findings: List[PydanticFinding],
        rule_findings: List[PydanticFinding]
    ) -> List[PydanticFinding]:
        """
        Merge findings from different sources and remove duplicates.
        
        Deduplication strategy: If two findings have the same severity and line number,
        keep only one (prefer the one with more detailed description).
        
        Args:
            slither_findings: Findings from Slither
            rule_findings: Findings from custom rules
            
        Returns:
            Deduplicated list of findings
        """
        all_findings = slither_findings + rule_findings
        
        # Use a dict to track unique findings by (severity, line_number)
        unique_findings = {}
        
        for finding in all_findings:
            # Create key for deduplication
            key = (finding.severity, finding.line_number)
            
            # If we haven't seen this finding before, add it
            if key not in unique_findings:
                unique_findings[key] = finding
            else:
                # If we have seen it, keep the one with longer description
                existing = unique_findings[key]
                if len(finding.description) > len(existing.description):
                    unique_findings[key] = finding
        
        # Sort by severity (critical first) and then by line number
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
        
        sorted_findings = sorted(
            unique_findings.values(),
            key=lambda f: (
                severity_order.get(f.severity, 5),
                f.line_number if f.line_number else 9999
            )
        )
        
        return sorted_findings
    
    def _calculate_severity_breakdown(self, findings: List[PydanticFinding]) -> Dict[str, int]:
        """
        Calculate count of findings by severity level.
        
        Args:
            findings: List of all findings
            
        Returns:
            Dictionary mapping severity levels to counts
        """
        breakdown = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0
        }
        
        for finding in findings:
            severity = finding.severity.lower()
            if severity in breakdown:
                breakdown[severity] += 1
        
        return breakdown
    
    def _calculate_score(self, findings: List[PydanticFinding]) -> int:
        """
        Calculate overall security score (0-100).
        
        Scoring algorithm:
        - Start at 100
        - Subtract 10 per critical
        - Subtract 5 per high
        - Subtract 2 per medium
        - Subtract 1 per low
        - Floor at 0
        
        Args:
            findings: List of all findings
            
        Returns:
            Security score from 0 to 100
        """
        score = 100
        
        severity_weights = {
            'critical': 10,
            'high': 5,
            'medium': 2,
            'low': 1,
            'info': 0
        }
        
        for finding in findings:
            severity = finding.severity.lower()
            weight = severity_weights.get(severity, 0)
            score -= weight
        
        # Floor at 0
        return max(0, score)
    
    def _generate_summary(self, severity_breakdown: Dict[str, int], score: int) -> str:
        """
        Generate a one-line summary of scan results.
        
        Args:
            severity_breakdown: Count of findings by severity
            score: Overall security score
            
        Returns:
            Human-readable summary string
        """
        critical = severity_breakdown.get('critical', 0)
        high = severity_breakdown.get('high', 0)
        medium = severity_breakdown.get('medium', 0)
        low = severity_breakdown.get('low', 0)
        
        # Build summary parts
        parts = []
        if critical > 0:
            parts.append(f"{critical} critical")
        if high > 0:
            parts.append(f"{high} high")
        if medium > 0:
            parts.append(f"{medium} medium")
        if low > 0:
            parts.append(f"{low} low")
        
        if not parts:
            return "No vulnerabilities found - SAFE ✅"
        
        findings_text = ", ".join(parts)
        
        # Determine safety status
        if score >= 80:
            status = "GOOD ✓"
        elif score >= 60:
            status = "MODERATE ⚠️"
        elif score >= 40:
            status = "RISKY ⚠️⚠️"
        else:
            status = "UNSAFE ❌"
        
        return f"{findings_text} - {status}"
    
    def _extract_contract_name(self, source_code: str) -> str:
        """
        Extract contract name from source code.
        
        Args:
            source_code: Solidity source code
            
        Returns:
            Extracted contract name or "Unknown"
        """
        import re
        
        # Simple regex to find contract declarations
        pattern = r'contract\s+(\w+)'
        match = re.search(pattern, source_code)
        
        if match:
            return match.group(1)
        
        return "Unknown"
    
    def __repr__(self) -> str:
        """String representation of orchestrator."""
        return f"AnalysisOrchestrator(rules={len(self.rules)}, slither_available={self.slither_wrapper.available})"
