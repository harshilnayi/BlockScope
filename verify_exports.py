"""
Verify that the backend.analysis module exports work correctly.

This script tests that:
1. AnalysisOrchestrator can be imported
2. ScanRequest can be imported
3. ScanResult can be imported
4. Finding can be imported
5. Basic functionality works
"""

import sys


def test_imports():
    """Test that all required exports can be imported."""
    print("=" * 70)
    print("TESTING BACKEND.ANALYSIS EXPORTS")
    print("=" * 70)
    print()

    # Test 1: Import AnalysisOrchestrator
    print("Test 1: Import AnalysisOrchestrator...")
    try:
        from backend.analysis import AnalysisOrchestrator

        print("✅ AnalysisOrchestrator imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AnalysisOrchestrator: {e}")
        return False

    # Test 2: Import ScanRequest
    print("\nTest 2: Import ScanRequest...")
    try:
        from backend.analysis import ScanRequest

        print("✅ ScanRequest imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ScanRequest: {e}")
        return False

    # Test 3: Import ScanResult
    print("\nTest 3: Import ScanResult...")
    try:
        from backend.analysis import ScanResult

        print("✅ ScanResult imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ScanResult: {e}")
        return False

    # Test 4: Import Finding
    print("\nTest 4: Import Finding...")
    try:
        from backend.analysis import Finding

        print("✅ Finding imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Finding: {e}")
        return False

    # Test 5: Create instances
    print("\nTest 5: Create instances...")
    try:
        orchestrator = AnalysisOrchestrator(rules=[])
        print(f"✅ Created orchestrator: {orchestrator}")

        request = ScanRequest(
            source_code="pragma solidity ^0.8.0; contract Test {}",
            contract_name="Test",
            file_path="/test.sol",
        )
        print(f"✅ Created ScanRequest: {request.contract_name}")

    except Exception as e:
        print(f"❌ Failed to create instances: {e}")
        return False

    # Test 6: Run analysis
    print("\nTest 6: Run analysis...")
    try:
        result = orchestrator.analyze(request)
        print(f"✅ Analysis completed successfully")
        print(f"   Contract: {result.contract_name}")
        print(f"   Score: {result.overall_score}/100")
        print(f"   Findings: {result.vulnerabilities_count}")
        print(f"   Summary: {result.summary}")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

    return True


def test_fastapi_integration():
    """Test that FastAPI can import the components."""
    print("\n" + "=" * 70)
    print("TESTING FASTAPI INTEGRATION")
    print("=" * 70)
    print()

    print("Simulating Jiten's import in backend/app/main.py...")
    try:
        # This is how Jiten will import in main.py
        from backend.analysis import AnalysisOrchestrator, ScanRequest, ScanResult

        print("✅ FastAPI imports work!")
        print(f"   AnalysisOrchestrator: {AnalysisOrchestrator}")
        print(f"   ScanRequest: {ScanRequest}")
        print(f"   ScanResult: {ScanResult}")

        return True
    except Exception as e:
        print(f"❌ FastAPI integration failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n🔍 BlockScope Export Verification\n")

    # Run tests
    imports_ok = test_imports()
    fastapi_ok = test_fastapi_integration()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if imports_ok and fastapi_ok:
        print("✅ All exports working correctly!")
        print("✅ Ready for FastAPI integration!")
        print()
        print("Next steps for Jiten:")
        print("1. Import in backend/app/main.py:")
        print("   from backend.analysis import AnalysisOrchestrator, ScanRequest, ScanResult")
        print()
        print("2. Create orchestrator with rules:")
        print("   orchestrator = AnalysisOrchestrator(rules=[...])")
        print()
        print("3. Use in /api/v1/scan endpoint:")
        print("   result = orchestrator.analyze(ScanRequest(...))")
        print()
        print("=" * 70)
        return 0
    else:
        print("❌ Some tests failed")
        print("Check the errors above and fix them")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
