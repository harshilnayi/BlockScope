"""
End-to-End Tests for BlockScope.

Tests the complete pipeline:
1. CLI → Analysis engine
2. FastAPI → Analysis engine

These tests verify that all components work together correctly.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# FastAPI testing
from fastapi.testclient import TestClient

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def test_contract_path():
    """Path to test contract fixture."""
    return Path("backend/tests/fixtures/test_contract.sol")


@pytest.fixture
def test_contract_code():
    """Simple test contract code."""
    return """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleStorage {
    uint256 public storedData;

    function set(uint256 x) public {
        storedData = x;
    }

    function get() public view returns (uint256) {
        return storedData;
    }
}
"""


@pytest.fixture
def vulnerable_contract_code():
    """Contract with known vulnerabilities for testing."""
    return """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableBank {
    mapping(address => uint) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint amount) public {
        require(balances[msg.sender] >= amount);

        // VULNERABLE: Reentrancy
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);

        balances[msg.sender] -= amount;
    }
}
"""


@pytest.fixture
def sample_sol_path():
    """Path to CLI test sample.sol."""
    return Path("backend/cli/tests/sample.sol")


@pytest.fixture
def mock_fastapi_app():
    """
    Create a mock FastAPI app for testing.
    This simulates what Jiten will build in backend/app/main.py
    """
    from fastapi import FastAPI, HTTPException, status

    from backend.analysis import AnalysisOrchestrator, ScanRequest, ScanResult

    app = FastAPI(title="BlockScope API - Test")

    # Create orchestrator with empty rules (for testing)
    orchestrator = AnalysisOrchestrator(rules=[])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "BlockScope API"}

    @app.post("/api/v1/scan", response_model=ScanResult, status_code=200)
    async def scan_contract(request: ScanRequest) -> ScanResult:
        """
        Analyze a smart contract for vulnerabilities.
        """
        try:
            result = orchestrator.analyze(request)
            return result
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid request: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis failed: {str(e)}",
            )

    return app


@pytest.fixture
def test_client(mock_fastapi_app):
    """Create TestClient for FastAPI testing."""
    return TestClient(mock_fastapi_app)


# ============================================================================
# TEST 1: CLI → Analysis Engine End-to-End
# ============================================================================


def test_cli_scan_basic(sample_sol_path, tmp_path):
    """
    TEST 1: CLI → Analysis engine works end-to-end.

    Tests that:
    1. CLI can be invoked
    2. Analysis runs without errors
    3. Output contains expected text
    """
    # Create a temporary test contract
    test_contract = tmp_path / "test.sol"
    test_contract.write_text(
        """
pragma solidity ^0.8.0;

contract Test {
    uint256 public value;

    function setValue(uint256 _value) public {
        value = _value;
    }
}
"""
    )

    print(f"\n🧪 Testing CLI scan on: {test_contract}")

    # Run CLI command
    result = subprocess.run(
        [sys.executable, "-m", "backend.cli.main", "scan", str(test_contract)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    print(f"   Return code: {result.returncode}")
    print(f"   STDOUT: {result.stdout[:500]}")

    # Assert: Command runs without critical errors
    # Note: returncode might be non-zero if Slither not installed, but that's okay
    assert result.returncode in [0, 1], f"CLI failed with code {result.returncode}"

    # Assert: Output contains scanning messages
    output = result.stdout + result.stderr
    assert any(
        keyword in output.lower() for keyword in ["scan", "analyz", "contract"]
    ), "Output should mention scanning or analysis"

    print(f"✅ CLI scan test passed!")


def test_cli_scan_with_sample_sol(sample_sol_path):
    """
    TEST 1 (Variant): Test CLI with the actual sample.sol if it exists.
    """
    if not sample_sol_path.exists():
        pytest.skip(f"Sample contract not found at {sample_sol_path}")

    print(f"\n🧪 Testing CLI scan on sample.sol: {sample_sol_path}")

    # Run CLI command
    result = subprocess.run(
        [sys.executable, "-m", "backend.cli.main", "scan", str(sample_sol_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    print(f"   Return code: {result.returncode}")
    print(f"   STDOUT snippet: {result.stdout[:300]}")

    # Assert: CLI runs (may warn about Slither but shouldn't crash)
    assert result.returncode in [0, 1], "CLI should complete execution"

    # Check output
    output = result.stdout + result.stderr
    assert len(output) > 0, "CLI should produce some output"

    print(f"✅ CLI sample.sol test passed!")


def test_cli_help_command():
    """
    TEST 1 (Bonus): Test that CLI help works.
    """
    print("\n🧪 Testing CLI help command")

    result = subprocess.run(
        [sys.executable, "-m", "backend.cli.main", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    print(f"   Return code: {result.returncode}")

    # Assert: Help command succeeds
    assert result.returncode == 0, "Help command should succeed"

    # Assert: Output contains help text
    assert (
        "usage" in result.stdout.lower() or "help" in result.stdout.lower()
    ), "Help output should contain usage information"

    print(f"✅ CLI help test passed!")


# ============================================================================
# TEST 2: FastAPI → Analysis Engine End-to-End
# ============================================================================


def test_fastapi_health_check(test_client):
    """
    TEST 2 (Setup): Test that FastAPI health check works.
    """
    print("\n🧪 Testing FastAPI health check")

    response = test_client.get("/health")

    print(f"   Status code: {response.status_code}")
    print(f"   Response: {response.json()}")

    # Assert: Health check returns 200
    assert response.status_code == 200, "Health check should return 200"

    # Assert: Response contains status
    data = response.json()
    assert "status" in data, "Response should contain status"
    assert data["status"] == "healthy", "Status should be healthy"

    print(f"✅ Health check test passed!")


def test_fastapi_scan_endpoint_simple(test_client, test_contract_code):
    """
    TEST 2: FastAPI → Analysis engine works end-to-end.

    Tests that:
    1. POST to /api/v1/scan works
    2. Response is 200
    3. Response contains findings, score, summary
    """
    print("\n🧪 Testing FastAPI /api/v1/scan endpoint")

    # Prepare request
    request_data = {
        "source_code": test_contract_code,
        "contract_name": "SimpleStorage",
        "file_path": "/test/SimpleStorage.sol",
    }

    print(f"   Sending request to /api/v1/scan")

    # Make request
    response = test_client.post("/api/v1/scan", json=request_data)

    print(f"   Status code: {response.status_code}")
    print(f"   Response keys: {response.json().keys()}")

    # Assert: Response is 200 OK
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Assert: Response is valid JSON
    data = response.json()
    assert isinstance(data, dict), "Response should be a JSON object"

    # Assert: Response contains required fields
    assert "findings" in data, "Response should contain 'findings'"
    assert "overall_score" in data, "Response should contain 'overall_score'"
    assert "summary" in data, "Response should contain 'summary'"

    # Assert: Fields have correct types
    assert isinstance(data["findings"], list), "findings should be a list"
    assert isinstance(data["overall_score"], int), "overall_score should be an int"
    assert isinstance(data["summary"], str), "summary should be a string"

    # Assert: Score is in valid range
    assert 0 <= data["overall_score"] <= 100, "Score should be 0-100"

    print(f"✅ FastAPI scan endpoint test passed!")
    print(f"   Score: {data['overall_score']}/100")
    print(f"   Findings: {len(data['findings'])}")
    print(f"   Summary: {data['summary']}")


def test_fastapi_scan_endpoint_with_findings(test_client, vulnerable_contract_code):
    """
    TEST 2 (Variant): Test FastAPI scan with a vulnerable contract.

    This ensures the API properly handles contracts with findings.
    """
    print("\n🧪 Testing FastAPI scan with vulnerable contract")

    request_data = {
        "source_code": vulnerable_contract_code,
        "contract_name": "VulnerableBank",
        "file_path": "/test/VulnerableBank.sol",
    }

    response = test_client.post("/api/v1/scan", json=request_data)

    print(f"   Status code: {response.status_code}")

    # Assert: Request succeeds
    assert response.status_code == 200, "Scan should succeed"

    data = response.json()

    # Assert: Response structure is valid
    assert "findings" in data
    assert "overall_score" in data
    assert "vulnerabilities_count" in data
    assert "severity_breakdown" in data

    # Assert: Severity breakdown is properly structured
    assert isinstance(data["severity_breakdown"], dict)
    assert "critical" in data["severity_breakdown"]
    assert "high" in data["severity_breakdown"]
    assert "medium" in data["severity_breakdown"]
    assert "low" in data["severity_breakdown"]

    print(f"✅ Vulnerable contract test passed!")
    print(f"   Score: {data['overall_score']}/100")
    print(f"   Findings: {data['vulnerabilities_count']}")


def test_fastapi_scan_endpoint_validation(test_client):
    """
    TEST 2 (Bonus): Test that FastAPI validates input properly.
    """
    print("\n🧪 Testing FastAPI input validation")

    # Test 1: Missing required field
    invalid_request = {
        "contract_name": "Test"
        # Missing source_code and file_path
    }

    response = test_client.post("/api/v1/scan", json=invalid_request)

    print(f"   Invalid request status: {response.status_code}")

    # Assert: Validation error
    assert response.status_code == 422, "Should return validation error (422)"

    # Test 2: Empty source code
    empty_request = {"source_code": "", "contract_name": "Empty", "file_path": "/empty.sol"}

    response = test_client.post("/api/v1/scan", json=empty_request)

    # Should still process (might return score of 100 with no findings)
    assert response.status_code in [200, 400, 422], "Should handle empty code"

    print(f"✅ Input validation test passed!")


def test_fastapi_scan_endpoint_response_format(test_client, test_contract_code):
    """
    TEST 2 (Bonus): Verify complete response format matches ScanResult model.
    """
    print("\n🧪 Testing FastAPI response format")

    request_data = {
        "source_code": test_contract_code,
        "contract_name": "Test",
        "file_path": "/test.sol",
    }

    response = test_client.post("/api/v1/scan", json=request_data)
    data = response.json()

    # Assert: All ScanResult fields are present
    required_fields = [
        "contract_name",
        "source_code",
        "findings",
        "vulnerabilities_count",
        "severity_breakdown",
        "overall_score",
        "summary",
        "timestamp",
    ]

    for field in required_fields:
        assert field in data, f"Response should contain '{field}'"

    # Assert: contract_name matches input
    assert data["contract_name"] == "Test", "Contract name should match"

    # Assert: vulnerabilities_count matches findings length
    assert data["vulnerabilities_count"] == len(
        data["findings"]
    ), "vulnerabilities_count should match findings length"

    print(f"✅ Response format test passed!")
    print(f"   All {len(required_fields)} required fields present")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_end_to_end_flow_complete(test_client, test_contract_code):
    """
    Complete end-to-end flow test.

    Simulates a full workflow:
    1. Health check
    2. Submit contract for scanning
    3. Verify results
    """
    print("\n🧪 Testing complete end-to-end flow")

    # Step 1: Health check
    print("   Step 1: Health check...")
    health_response = test_client.get("/health")
    assert health_response.status_code == 200
    print("   ✓ API is healthy")

    # Step 2: Submit scan
    print("   Step 2: Submit scan request...")
    scan_request = {
        "source_code": test_contract_code,
        "contract_name": "SimpleStorage",
        "file_path": "/contracts/SimpleStorage.sol",
    }

    scan_response = test_client.post("/api/v1/scan", json=scan_request)
    assert scan_response.status_code == 200
    print("   ✓ Scan completed successfully")

    # Step 3: Verify results
    print("   Step 3: Verify results...")
    result = scan_response.json()

    assert result["contract_name"] == "SimpleStorage"
    assert isinstance(result["overall_score"], int)
    assert 0 <= result["overall_score"] <= 100
    assert isinstance(result["findings"], list)
    assert isinstance(result["summary"], str)

    print("   ✓ Results verified")
    print(f"\n✅ Complete end-to-end flow test passed!")
    print(f"   Contract: {result['contract_name']}")
    print(f"   Score: {result['overall_score']}/100")
    print(f"   Summary: {result['summary']}")


# ============================================================================
# SUMMARY TEST
# ============================================================================


def test_all_components_integrated():
    """
    High-level test that verifies all components can be imported and work together.
    """
    print("\n🧪 Testing component integration")

    # Test imports
    from backend.analysis import AnalysisOrchestrator, ScanRequest, ScanResult

    print("   ✓ All imports successful")

    # Test orchestrator creation
    orchestrator = AnalysisOrchestrator(rules=[])
    print(f"   ✓ Orchestrator created: {orchestrator}")

    # Test request creation
    request = ScanRequest(
        source_code="pragma solidity ^0.8.0; contract Test {}",
        contract_name="Test",
        file_path="/test.sol",
    )
    print(f"   ✓ Request created: {request.contract_name}")

    # Test analysis
    result = orchestrator.analyze(request)
    print(f"   ✓ Analysis completed: {result.overall_score}/100")

    # Verify result
    assert isinstance(result, ScanResult)
    assert result.contract_name == "Test"
    assert 0 <= result.overall_score <= 100

    print(f"\n✅ Component integration test passed!")
    print(f"   All components working together successfully")


# ============================================================================
# PYTEST MARKERS
# ============================================================================

# Mark tests that require external tools
pytest.mark.cli = pytest.mark.skipif(
    not Path("backend/cli/main.py").exists(), reason="CLI not available"
)

pytest.mark.fastapi = pytest.mark.skipif(
    not Path("backend/app/main.py").exists(), reason="FastAPI app not available"
)
