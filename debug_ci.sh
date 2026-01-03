#!/bin/bash
# Debug script to test CI locally before pushing

echo "=========================================="
echo "BLOCKSCOPE CI DEBUG"
echo "=========================================="
echo ""

# Check Python version
echo "1. Python version:"
python --version
echo ""

# Check if we're in the right directory
echo "2. Current directory:"
pwd
echo ""

# Check if backend exists
echo "3. Backend directory:"
ls -la backend/ | head -10
echo ""

# Set PYTHONPATH
export PYTHONPATH=$PWD
echo "4. PYTHONPATH set to: $PYTHONPATH"
echo ""

# Install dependencies
echo "5. Installing dependencies..."
pip install -q pytest httpx pydantic fastapi click
if [ -f backend/requirements.txt ]; then
    pip install -q -r backend/requirements.txt
fi
echo "✅ Dependencies installed"
echo ""

# Check what's installed
echo "6. Key packages:"
pip list | grep -E "pytest|httpx|pydantic|fastapi|click"
echo ""

# Create directories
echo "7. Creating test directories..."
mkdir -p backend/tests/fixtures
mkdir -p backend/cli/tests
mkdir -p backend/analysis/tests/fixtures
echo "✅ Directories created"
echo ""

# Try importing
echo "8. Testing imports..."
python -c "from backend.analysis import AnalysisOrchestrator; print('✅ AnalysisOrchestrator imports')" || echo "❌ Import failed"
python -c "from backend.analysis import ScanRequest, ScanResult; print('✅ Models import')" || echo "❌ Models import failed"
python -c "from fastapi.testclient import TestClient; print('✅ TestClient imports')" || echo "❌ TestClient import failed"
echo ""

# List test files
echo "9. Test files found:"
find backend -name "test_*.py" -type f
echo ""

# Try running tests one by one
echo "10. Running tests..."
echo ""

echo "=== Test: orchestrator ==="
python -m pytest backend/analysis/tests/test_orchestrator.py -v --tb=line 2>&1 | tail -20
echo ""

echo "=== Test: E2E ==="
python -m pytest backend/tests/test_e2e.py -v --tb=line 2>&1 | tail -20
echo ""

echo "=== Test: base ==="
python -m pytest backend/analysis/tests/test_base.py -v --tb=line 2>&1 | tail -20 || echo "Base tests failed (might be OK)"
echo ""

echo "=========================================="
echo "DEBUG COMPLETE"
echo "=========================================="
