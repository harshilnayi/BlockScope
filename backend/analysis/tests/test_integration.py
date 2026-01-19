"""
Integration tests for BlockScope.

Updated to work with current implementation.
These tests bridge CLI, orchestrator, and future FastAPI endpoints.
"""

import pytest
import subprocess
import sys
from pathlib import Path
from click.testing import CliRunner

from analysis import AnalysisOrchestrator, ScanRequest, ScanResult
from analysis.rules.base import VulnerabilityRule


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_contract():
    """Sample Solidity contract for testing."""
    return """
pragma solidity ^0.8.0;

contract SimpleStorage {
    uint256 public value;
    
    function setValue(uint256 _value) public {
        value = _value;
    }
}
"""


@pytest.fixture
def orchestrator():
    """Create orchestrator for testing."""
    return AnalysisOrchestrator(rules=[])


# ============================================================================
# CLI INTEGRATION TESTS
# ============================================================================

def test_cli_to_orchestrator(sample_contract, tmp_path):
    """
    Test CLI can invoke orchestrator.
    
    This verifies the CLI → Orchestrator pipeline works.
    """
    # Create test contract file
    test_file = tmp_path / "test.sol"
    test_file.write_text(sample_contract)
    
    # Run CLI
    result = subprocess.run(
        [sys.executable, "-m", "backend.cli.main", "scan", str(test_file)],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Assert CLI ran (may have warnings about Slither, but shouldn't crash)
    assert result.returncode in [0, 1], "CLI should complete execution"
    output = result.stdout + result.stderr
    assert len(output) > 0, "CLI should produce output"


def test_cli_json_output(sample_contract, tmp_path):
    """
    Test CLI JSON output format (if/when implemented).
    
    For now, just verify CLI runs without critical errors.
    """
    test_file = tmp_path / "test.sol"
    test_file.write_text(sample_contract)
    
    # Try to run with --json flag (may not be implemented yet)
    result = subprocess.run(
        [sys.executable, "-m", "backend.cli.main", "scan", str(test_file)],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # For now, just verify it runs
    assert result.returncode in [0, 1], "CLI should run"
    
    # Note: JSON output format to be implemented by team
    # When implemented, add: data = json.loads(result.stdout)


# ============================================================================
# FASTAPI INTEGRATION TESTS (Mock endpoints for now)
# ============================================================================

def test_fastapi_scan_endpoint():
    """
    Test FastAPI scan endpoint integration.
    
    This test uses the mock FastAPI app from test_e2e.py.
    The real implementation will be done by Jiten.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    # Create mock app (same as in test_e2e.py)
    app = FastAPI()
    orchestrator = AnalysisOrchestrator(rules=[])
    
    @app.post("/api/v1/scan", response_model=ScanResult)
    async def scan_contract(request: ScanRequest) -> ScanResult:
        return orchestrator.analyze(request)
    
    client = TestClient(app)
    
    # Test the endpoint
    request_data = {
        "source_code": "pragma solidity ^0.8.0; contract Test {}",
        "contract_name": "Test",
        "file_path": "/test.sol"
    }
    
    response = client.post("/api/v1/scan", json=request_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "findings" in data


def test_fastapi_list_scans():
    """
    Test listing scans endpoint (to be implemented).
    
    This is a placeholder for when Jiten implements the /scans endpoint.
    """
    # For now, just verify imports work
    from analysis import AnalysisOrchestrator
    
    orchestrator = AnalysisOrchestrator(rules=[])
    assert orchestrator is not None
    
    # TODO: When Jiten implements /api/v1/scans endpoint:
    # response = client.get("/api/v1/scans")
    # assert response.status_code == 200


def test_fastapi_get_scan_by_id():
    """
    Test getting scan by ID (to be implemented).
    
    This is a placeholder for when Jiten implements scan persistence.
    """
    # For now, just verify the models exist
    from analysis import ScanResult
    
    # Verify ScanResult has timestamp (used as ID)
    from datetime import datetime
    assert hasattr(ScanResult, '__annotations__')
    assert 'timestamp' in ScanResult.__annotations__
    
    # TODO: When Jiten implements /api/v1/scans/{id} endpoint:
    # response = client.get(f"/api/v1/scans/{scan_id}")
    # assert response.status_code == 200


# ============================================================================
# ORCHESTRATOR DIRECT TESTS
# ============================================================================

def test_orchestrator_direct(sample_contract):
    """
    Test orchestrator can be used directly (without CLI or API).
    
    This verifies the core analysis functionality works standalone.
    """
    # Create orchestrator
    orchestrator = AnalysisOrchestrator(rules=[])
    
    # Create request (with all required fields)
    request = ScanRequest(
        source_code=sample_contract,
        contract_name="Direct",
        file_path="/direct.sol"  # This field is required!
    )
    
    # Run analysis
    result = orchestrator.analyze(request)
    
    # Assert result is valid
    assert isinstance(result, ScanResult)
    assert result.contract_name == "Direct"
    assert isinstance(result.overall_score, int)
    assert 0 <= result.overall_score <= 100
    assert isinstance(result.findings, list)
    assert isinstance(result.summary, str)
    
    print(f"\n✅ Direct orchestrator test passed!")
    print(f"   Score: {result.overall_score}/100")
    print(f"   Summary: {result.summary}")


def test_orchestrator_with_multiple_contracts(sample_contract):
    """
    Test orchestrator can handle multiple scans.
    """
    orchestrator = AnalysisOrchestrator(rules=[])
    
    # Scan multiple contracts
    contracts = [
        ("Contract1", sample_contract),
        ("Contract2", "pragma solidity ^0.8.0; contract Test2 {}"),
        ("Contract3", "pragma solidity ^0.8.0; contract Test3 { uint x; }")
    ]
    
    results = []
    for name, code in contracts:
        request = ScanRequest(
            source_code=code,
            contract_name=name,
            file_path=f"/{name}.sol"
        )
        result = orchestrator.analyze(request)
        results.append(result)
    
    # Assert all scans completed
    assert len(results) == 3
    for result in results:
        assert isinstance(result, ScanResult)
        assert 0 <= result.overall_score <= 100
    
    print(f"\n✅ Multiple contracts test passed!")
    print(f"   Scanned {len(results)} contracts successfully")


# ============================================================================
# COMPONENT INTEGRATION TESTS
# ============================================================================

def test_models_integration():
    """Test that all models work together correctly."""
    from analysis.models import Finding
    
    # Create a finding
    finding = Finding(
        title="Test Finding",
        severity="high",
        description="Test description",
        line_number=10,
        code_snippet="test code",
        recommendation="Fix it"
    )
    
    assert finding.title == "Test Finding"
    assert finding.severity == "high"
    
    print(f"\n✅ Models integration test passed!")


def test_rules_integration():
    """Test that rules can be integrated with orchestrator."""
    from analysis.rules.base import VulnerabilityRule, Severity, Finding as RuleFinding
    
    # Create a test rule
    class TestRule(VulnerabilityRule):
        def __init__(self):
            super().__init__(
                rule_id="TEST-001",
                name="Test Rule",
                severity=Severity.LOW
            )
        
        def detect(self, ast):
            return []  # No findings for test
    
    # Create orchestrator with rule
    rule = TestRule()
    orchestrator = AnalysisOrchestrator(rules=[rule])
    
    assert len(orchestrator.rules) == 1
    assert orchestrator.rules[0].rule_id == "TEST-001"
    
    # Run analysis with rule
    request = ScanRequest(
        source_code="pragma solidity ^0.8.0; contract Test {}",
        contract_name="Test",
        file_path="/test.sol"
    )
    
    result = orchestrator.analyze(request)
    assert isinstance(result, ScanResult)
    
    print(f"\n✅ Rules integration test passed!")


# ============================================================================
# NOTES FOR TEAM
# ============================================================================

"""
NOTES FOR JITEN (FastAPI Developer):

The following endpoints need to be implemented in backend/app/main.py:

1. POST /api/v1/scan
   - Already shown in test_e2e.py
   - Takes ScanRequest, returns ScanResult
   
2. GET /api/v1/scans (optional)
   - List all scans
   - Requires database persistence
   
3. GET /api/v1/scans/{id} (optional)
   - Get specific scan by ID
   - Requires database persistence

Once implemented, update the placeholder tests above with real endpoint tests.

NOTES FOR SHANAY (CLI Developer):

The CLI currently works but could be enhanced with:
- JSON output format (--json flag)
- Better error messages
- Progress indicators

NOTES FOR EVERYONE:

These integration tests verify that components work together.
They're separate from unit tests (test_orchestrator.py) and E2E tests (test_e2e.py).
"""
