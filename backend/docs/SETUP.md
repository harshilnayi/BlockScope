# Development Setup Guide (Windows)

## Prerequisites
- Python 3.11+ installed
- Git installed
- Terminal/PowerShell

## Setup Steps

### 1. Clone Repository
\`\`\`powershell
git clone https://github.com/harshilnayi/BlockScope.git
cd BlockScope
\`\`\`

### 2. Create Virtual Environment
\`\`\`powershell
cd backend
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# You should see (venv) in your terminal
\`\`\`

### 3. Install Dependencies
\`\`\`powershell
pip install -r requirements.txt
\`\`\`

### 4. Verify Installation
\`\`\`powershell
pip list  # Should show fastapi, sqlalchemy, pytest, etc.
\`\`\`

### 5. Run Tests
\`\`\`powershell
# Make sure venv is activated
pytest analysis/tests/ -v
pytest cli/tests/ -v
\`\`\`

### 6. Run FastAPI
\`\`\`powershell
python -m uvicorn app.main:app --reload

# Visit: http://localhost:8000/docs
\`\`\`

### 7. Run CLI
\`\`\`powershell
python -m cli.main scan test.sol
\`\`\`

## Common Issues

### "python: command not found"
- Make sure Python 3.11+ is installed
- Check: python --version

### "pip not found"
- Ensure virtual environment is activated: .\venv\Scripts\activate

### "Module not found errors"
- Reinstall dependencies: pip install -r requirements.txt

## Code Quality

### Run Linting
\`\`\`powershell
flake8 . --count
\`\`\`

### Run Type Checking
\`\`\`powershell
mypy . --ignore-missing-imports
\`\`\`

### Format Code
\`\`\`powershell
black .
\`\`\`
