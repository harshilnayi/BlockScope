"""
Quick E2E Test Runner for BlockScope.

Run this from project root: python run_e2e_tests.py
"""

import subprocess
import sys
from pathlib import Path


def setup_directories():
    """Ensure all necessary directories exist."""
    print("📁 Setting up directories...")

    directories = ["backend/tests", "backend/tests/fixtures", "backend/cli/tests"]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        init_file = Path(directory) / "__init__.py"
        if not init_file.exists():
            init_file.touch()

    print("✅ Directories ready")


def check_dependencies():
    """Check if required packages are installed."""
    print("\n📦 Checking dependencies...")

    required = ["pytest", "httpx", "fastapi"]
    missing = []

    for package in required:
        try:
            __import__(package)
            print(f"   ✓ {package}")
        except ImportError:
            print(f"   ✗ {package} (missing)")
            missing.append(package)

    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        response = input("Install them now? (y/n): ")
        if response.lower() == "y":
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing)
            print("✅ Packages installed")
        else:
            print("❌ Cannot run tests without required packages")
            return False
    else:
        print("✅ All dependencies installed")

    return True


def run_tests():
    """Run the E2E tests."""
    print("\n" + "=" * 70)
    print("BLOCKSCOPE END-TO-END TESTS")
    print("=" * 70)
    print()

    # Check directory
    if not Path("backend").exists():
        print("❌ Error: Must run from project root (E:\\BlockScope)")
        print(f"   Current directory: {Path.cwd()}")
        return 1

    # Setup
    setup_directories()

    # Check dependencies
    if not check_dependencies():
        return 1

    # Check test file exists
    test_file = Path("backend/tests/test_e2e.py")
    if not test_file.exists():
        print(f"\n❌ Test file not found: {test_file}")
        print("   Copy test_e2e.py to backend/tests/")
        return 1

    print(f"\n✅ Test file found: {test_file}")

    # Run tests
    print("\n" + "=" * 70)
    print("RUNNING TESTS")
    print("=" * 70)
    print()

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "-s"], capture_output=False
    )

    print("\n" + "=" * 70)

    if result.returncode == 0:
        print("✅ ALL E2E TESTS PASSED! 🎉")
        print("=" * 70)
        print()
        print("Task 5 Complete:")
        print("  ✅ CLI → Analysis engine working")
        print("  ✅ FastAPI → Analysis engine working")
        print("  ✅ All components integrated")
        print()
        print("🚀 BlockScope is production ready!")
        print()
        print("Next steps:")
        print("  1. Add more vulnerability rules")
        print("  2. Integrate ML models")
        print("  3. Build frontend interface")
        print("  4. Deploy to production")
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        print()
        print("Check the output above for details")
        print()
        print("Common issues:")
        print("  - Missing dependencies (run: pip install pytest httpx fastapi)")
        print("  - Wrong directory (run from: E:\\BlockScope)")
        print("  - Missing test files (copy test_e2e.py to backend/tests/)")

    print()
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
