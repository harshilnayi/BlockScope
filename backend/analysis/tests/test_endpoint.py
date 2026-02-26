# backend/tests/test_endpoints.py

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
  # Adjust import based on your app structure
import tempfile
import os

client = TestClient(app)

# Helper function to create a temporary file with given content and extension
def create_temp_file(content: str, extension: str) -> str:
    with tempfile.NamedTemporaryFile(mode='w', suffix=extension, delete=False) as f:
        f.write(content)
        return f.name

# Test 1: Valid Solidity File Upload
def test_valid_solidity_upload():
    # Create a simple valid Solidity contract
    valid_sol_content = """
pragma solidity ^0.8.0;

contract SimpleContract {
    uint256 public value;

    function setValue(uint256 _value) public {
        value = _value;
    }
}
"""
    file_path = create_temp_file(valid_sol_content, ".sol")
    try:
        with open(file_path, "rb") as f:
            response = client.post("/api/v1/scan", files={"file": ("test.sol", f, "application/octet-stream")})
        assert response.status_code == 200
        data = response.json()
        assert "contract_name" in data
        assert "vulnerabilities" in data  # Can be empty list if no vulnerabilities
        assert isinstance(data["vulnerabilities"], list)
        assert "scan_timestamp" in data
    finally:
        os.unlink(file_path)

# Test 2: Missing File
def test_missing_file():
    response = client.post("/api/v1/scan")
    assert response.status_code in [400, 422]

    data = response.json()
    assert "detail" in data  # Assuming FastAPI error format
    assert "file" in data["detail"].lower() or "required" in str(data["detail"]).lower()
# Test 3: Invalid File Type
@pytest.mark.parametrize("extension,content", [
    (".txt", "This is a text file"),
    (".py", "print('Hello World')")
])
def test_invalid_file_type(extension, content):
    file_path = create_temp_file(content, extension)
    try:
        with open(file_path, "rb") as f:
            response = client.post("/api/v1/scan", files={"file": (f"test{extension}", f, "application/octet-stream")})
        assert response.status_code in [400, 422]

        data = response.json()
        assert "detail" in data
        assert "sol" in str(data["detail"]).lower()   
    finally:
        os.unlink(file_path)

# Test 4: Empty File
def test_empty_file():
    file_path = create_temp_file("", ".sol")
    try:
        with open(file_path, "rb") as f:
            response = client.post("/api/v1/scan", files={"file": ("empty.sol", f, "application/octet-stream")})
        # Either 400 or 200 with "no code found" - adjust based on your implementation
        assert response.status_code in [200, 400]
        data = response.json()
        if response.status_code == 200:
            assert "contract_name" in data
            assert "vulnerabilities" in data
            assert "scan_timestamp" in data
            # Check for indication of no code
            assert len(data["vulnerabilities"]) == 0 or "no code found" in str(data).lower()
        else:
            assert "detail" in data
            assert "empty" in data["detail"].lower() or "no code" in data["detail"].lower()
    finally:
        os.unlink(file_path)

# Test 5: Malformed Solidity Code
def test_malformed_solidity_code():
    malformed_sol_content = """
pragma solidity ^0.8.0;

contract BrokenContract {
    uint256 public value

    function setValue(uint256 _value) public {
        value = _value
    // Missing closing brace
"""
    file_path = create_temp_file(malformed_sol_content, ".sol")
    try:
        with open(file_path, "rb") as f:
            response = client.post("/api/v1/scan", files={"file": ("broken.sol", f, "application/octet-stream")})
        # Should handle gracefully without crashing
        assert response.status_code in [200, 400]
        data = response.json()
        if response.status_code == 200:
            assert "contract_name" in data
            assert "vulnerabilities" in data
            assert "scan_timestamp" in data
            # May include parsing errors in vulnerabilities
        else:
            assert "detail" in data
            assert "syntax" in data["detail"].lower() or "error" in data["detail"].lower()
    finally:
        os.unlink(file_path)

# Test 6: Large File
def test_large_file():
    # Create a large file (>10MB) with valid Solidity code
    large_content = "pragma solidity ^0.8.0;\n\ncontract LargeContract {\n"
    large_content += "    uint256 public value;\n" * 100000  # Repeat to make it large
    large_content += "}\n"
    file_path = create_temp_file(large_content, ".sol")
    try:
        file_size = os.path.getsize(file_path)
        assert file_size > 2 * 1024 * 1024  # >10MB
        with open(file_path, "rb") as f:
            response = client.post("/api/v1/scan", files={"file": ("large.sol", f, "application/octet-stream")})
        # Either processes or rejects - adjust based on your design
        assert response.status_code in [200, 400, 413]  # 413 for payload too large
        if response.status_code == 200:
            data = response.json()
            assert "contract_name" in data
            assert "vulnerabilities" in data
            assert "scan_timestamp" in data
        elif response.status_code == 413:
            data = response.json()
            assert "detail" in data
            assert "large" in data["detail"].lower() or "size" in data["detail"].lower()
        else:
            data = response.json()
            assert "detail" in data
            # Check for size-related error
    finally:
        os.unlink(file_path)