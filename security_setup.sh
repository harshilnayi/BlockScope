#!/bin/bash

# ===================================
# BLOCKSCOPE SECURITY SETUP SCRIPT
# ===================================
# This script automates the security configuration setup
# Run: bash security_setup.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

generate_secret_key() {
    python3 -c "import secrets; print(secrets.token_urlsafe(64))"
}

# ===================================
# 1. Check Prerequisites
# ===================================
print_header "Checking Prerequisites"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
else
    print_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    print_success "pip found"
else
    print_error "pip not found. Please install pip"
    exit 1
fi

# Check PostgreSQL
if command -v psql &> /dev/null; then
    print_success "PostgreSQL client found"
else
    print_warning "PostgreSQL client not found. Make sure PostgreSQL is accessible"
fi

# Check Redis
if command -v redis-cli &> /dev/null; then
    print_success "Redis client found"
else
    print_warning "Redis client not found. Make sure Redis is accessible"
fi

# ===================================
# 2. Setup Backend Environment
# ===================================
print_header "Setting Up Backend Environment"

cd backend 2>/dev/null || print_warning "backend/ directory not found"

# Generate .env.development if it doesn't exist
if [ ! -f .env.development ]; then
    print_success "Generating .env.development..."

    SECRET_KEY=$(generate_secret_key)
    JWT_SECRET_KEY=$(generate_secret_key)

    cat > .env.development << EOL
# Auto-generated development environment file
# Generated on: $(date)

# Application
APP_NAME=BlockScope
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=DEBUG

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=1
RELOAD=True

# Database
DATABASE_URL=postgresql://blockscope_dev:dev_password@localhost:5432/blockscope_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Rate Limiting (disabled in dev)
RATE_LIMIT_ENABLED=False

# File Upload
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=.sol
UPLOAD_FOLDER=/tmp/blockscope_dev_uploads

# Slither
SLITHER_TIMEOUT=300

# Logging
LOG_FILE_ENABLED=True
LOG_FILE_PATH=./logs/blockscope_dev.log
LOG_JSON_FORMAT=False

# Feature Flags
ENABLE_API_DOCS=True
ENABLE_METRICS=True
EOL

    print_success "Created .env.development"
    print_warning "SECRET_KEY and JWT_SECRET_KEY have been generated"
else
    print_warning ".env.development already exists, skipping"
fi

# ===================================
# 3. Install Python Dependencies
# ===================================
print_header "Installing Python Dependencies"

if [ -f requirements.txt ]; then
    print_success "Installing from requirements.txt..."
    pip3 install -r requirements.txt --break-system-packages
    print_success "Dependencies installed"
else
    print_warning "requirements.txt not found"
fi

# ===================================
# 4. Setup Pre-commit Hooks
# ===================================
print_header "Setting Up Pre-commit Hooks"

if command -v pre-commit &> /dev/null; then
    cd ..
    if [ -f .pre-commit-config.yaml ]; then
        print_success "Installing pre-commit hooks..."
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning ".pre-commit-config.yaml not found"
    fi
else
    print_warning "pre-commit not installed. Install with: pip install pre-commit"
fi

# ===================================
# 5. Initialize Database
# ===================================
print_header "Database Setup"

print_warning "Creating PostgreSQL database..."
echo "Run these commands manually:"
echo ""
echo "createdb blockscope_dev"
echo "psql blockscope_dev -c \"CREATE USER blockscope_dev WITH PASSWORD 'dev_password';\""
echo "psql blockscope_dev -c \"GRANT ALL PRIVILEGES ON DATABASE blockscope_dev TO blockscope_dev;\""
echo ""

# ===================================
# 6. Setup Logging Directory
# ===================================
print_header "Setting Up Logging"

mkdir -p backend/logs
print_success "Created logs directory"

# ===================================
# 7. Setup Upload Directory
# ===================================
print_header "Setting Up Upload Directory"

mkdir -p /tmp/blockscope_dev_uploads
print_success "Created uploads directory"

# ===================================
# 8. Generate Secrets Baseline
# ===================================
print_header "Generating Secrets Baseline"

if command -v detect-secrets &> /dev/null; then
    detect-secrets scan > .secrets.baseline 2>/dev/null || true
    print_success "Created .secrets.baseline"
else
    print_warning "detect-secrets not installed"
fi

# ===================================
# 9. Security Checklist
# ===================================
print_header "Security Checklist"

echo ""
echo "Please complete the following security tasks:"
echo ""
echo "[ ] 1. Review and update .env.development with actual values"
echo "[ ] 2. Create .env.production with secure credentials"
echo "[ ] 3. Never commit .env files"
echo "[ ] 4. Setup PostgreSQL database"
echo "[ ] 5. Setup Redis instance"
echo "[ ] 6. Install and configure pre-commit hooks"
echo "[ ] 7. Run security scan: safety check"
echo "[ ] 8. Review SECURITY.md"
echo "[ ] 9. Test API key generation"
echo "[ ] 10. Configure CORS origins for production"
echo ""

# ===================================
# 10. Generate SECRET_KEY Commands
# ===================================
print_header "Generate New Secret Keys"

echo ""
echo "To generate new secret keys, run:"
echo ""
echo "python3 -c \"import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))\""
echo "python3 -c \"import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))\""
echo ""

# ===================================
# 11. Next Steps
# ===================================
print_header "Next Steps"

echo ""
echo "1. Start PostgreSQL:"
echo "   docker-compose up -d db"
echo ""
echo "2. Start Redis:"
echo "   docker-compose up -d redis"
echo ""
echo "3. Run database migrations:"
echo "   cd backend && alembic upgrade head"
echo ""
echo "4. Start backend:"
echo "   cd backend && uvicorn app.main:app --reload"
echo ""
echo "5. Visit API docs:"
echo "   http://localhost:8000/docs"
echo ""

# ===================================
# 12. Summary
# ===================================
print_header "Setup Complete!"

print_success "Security setup completed successfully!"
print_warning "Remember to:"
echo "  - Update .env.development with actual database credentials"
echo "  - Create .env.production before deploying"
echo "  - Run 'pre-commit install' to enable pre-commit hooks"
echo "  - Review SECURITY.md for security best practices"
echo ""
echo "For help, see: README.md or SECURITY.md"
echo ""

# Generate summary file
cat > SECURITY_SETUP_SUMMARY.txt << EOL
# BlockScope Security Setup Summary
# Generated: $(date)

## Files Created:
✅ .env.development (backend)
✅ .secrets.baseline (if detect-secrets installed)
✅ logs/ directory
✅ /tmp/blockscope_dev_uploads/ directory

## Generated Secrets:
⚠️  SECRET_KEY: Generated and saved in .env.development
⚠️  JWT_SECRET_KEY: Generated and saved in .env.development

## Next Actions Required:
1. Update DATABASE_URL in .env.development
2. Create .env.production for production deployment
3. Setup PostgreSQL database
4. Setup Redis instance
5. Install pre-commit hooks: pre-commit install
6. Run security scan: safety check
7. Review and test all security configurations

## Important Security Reminders:
❌ NEVER commit .env files
❌ NEVER use development secrets in production
✅ ALWAYS use strong, unique secrets
✅ ALWAYS enable HTTPS in production
✅ ALWAYS keep dependencies updated

## Support:
- Documentation: README.md
- Security Policy: SECURITY.md
- Report Issues: GitHub Issues
EOL

print_success "Created SECURITY_SETUP_SUMMARY.txt"
