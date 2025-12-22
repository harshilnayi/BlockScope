# BlockScope Architecture

## 🏗️ System Overview

BlockScope is a distributed vulnerability scanning system with three main layers:

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend Layer (React)                 │
│  - Web UI, Dashboard, Report Viewer, Upload Interface   │
└────────────────────┬────────────────────────────────────┘
                     │ REST API (FastAPI)
┌────────────────────┴────────────────────────────────────┐
│                  Backend Layer (Python)                  │
│  - API Routes, User Management, Report Generation       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──────┐ ┌──▼────────┐ ┌─▼──────────┐
│  Analysis    │ │  ML       │ │  Database  │
│  Engine      │ │  Pipeline │ │  Layer     │
└──────────────┘ └───────────┘ └────────────┘
```

## 📦 Components

### 1. Frontend Layer
**Technology**: React 18 + TailwindCSS + Vite

**Components**:
- Dashboard (scan stats, recent history)
- Upload page (drag-drop interface)
- Scan results viewer (detailed findings)
- Report exporter (PDF, JSON, CSV)
- User authentication
- Admin panel

**Key Features**:
- Real-time scan progress
- Interactive vulnerability details
- Code snippet highlighting
- Remediation suggestions
- Scan history management

### 2. Backend API
**Technology**: Python 3.11 + FastAPI + Uvicorn

**Core Modules**:

```
backend/
├── app/
│   ├── api/
│   │   ├── auth.py          # JWT authentication
│   │   ├── scans.py         # Scan endpoints
│   │   ├── reports.py       # Report management
│   │   └── users.py         # User management
│   ├── core/
│   │   ├── config.py        # Environment config
│   │   └── security.py      # JWT, CORS, etc
│   ├── models/
│   │   ├── scan.py          # SQLAlchemy models
│   │   ├── finding.py       # Vulnerability findings
│   │   └── user.py          # User accounts
│   ├── schemas/
│   │   ├── scan_schema.py   # Pydantic validation
│   │   └── finding_schema.py
│   ├── services/
│   │   ├── scan_service.py  # Business logic
│   │   ├── report_service.py
│   │   └── ml_service.py
│   └── utils/
│       ├── cache.py         # Redis caching
│       └── logger.py        # Structured logging
└── main.py                  # FastAPI app entry
```

**Key Endpoints**:
```
POST   /api/v1/scans              # Create new scan
GET    /api/v1/scans/{id}         # Get scan results
POST   /api/v1/scans/{id}/export  # Export report
GET    /api/v1/history            # Scan history
POST   /api/v1/auth/login         # User login
```

### 3. Analysis Engine
**Technology**: Python + Slither + Custom AST Parser

**Workflow**:
```
Input (Solidity Code)
    ↓
[Source Code Parser] → AST (Abstract Syntax Tree)
    ↓
[Pattern Matcher] → Finds suspicious patterns
    ↓
[Rule Engine] → Applies detection rules
    ↓
[Findings] → Vulnerability reports
    ↓
[ML Pipeline] → Severity ranking + false positive detection
    ↓
Output (Structured findings)
```

**Detection Rules**:
```
analysis/
├── rules/
│   ├── reentrancy.py        # Reentrancy detection
│   ├── overflow.py          # Integer overflow/underflow
│   ├── access_control.py    # Missing modifiers
│   ├── delegatecall.py      # Dangerous delegatecall
│   ├── external_calls.py    # Unchecked calls
│   ├── timestamp.py         # Timestamp dependency
│   ├── flash_loan.py        # Flash loan patterns
│   └── erc20.py             # ERC-20 issues
├── slither_wrapper.py       # Slither integration
├── ast_parser.py            # Custom AST parsing
└── severity_calculator.py   # Severity ranking
```

### 4. Machine Learning Pipeline
**Technology**: scikit-learn + pandas + numpy

**Purpose**: 
- Predict vulnerability severity
- Detect false positives
- Rank findings by confidence

**Training Data**:
- Real-world exploits (known vulnerable contracts)
- Audit reports (OpenZeppelin, Trail of Bits, etc.)
- Bug bounties (Immunefi, HackerOne data)

**Model Pipeline**:
```
[Training Data]
    ↓
[Feature Extraction]
    ↓
[Classification Model]
    ↓
[Severity Predictor]
    ↓
[Confidence Scorer]
    ↓
[Inference on new findings]
```

**Features Used**:
- Vulnerability type (reentrancy, overflow, etc.)
- Contract complexity (LOC, function count)
- Risk exposure (external calls, state changes)
- Historical accuracy (similar contracts)

### 5. Database Layer
**Technology**: PostgreSQL + Redis

**Schema Overview**:

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Scans table
CREATE TABLE scans (
    id UUID PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    contract_name VARCHAR(255),
    source_code TEXT,
    status ENUM('pending', 'scanning', 'completed', 'failed'),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Findings table
CREATE TABLE findings (
    id UUID PRIMARY KEY,
    scan_id UUID REFERENCES scans(id),
    vulnerability_type VARCHAR(100),
    severity ENUM('critical', 'high', 'medium', 'low'),
    confidence FLOAT,
    line_number INTEGER,
    code_snippet TEXT,
    remediation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reports table
CREATE TABLE reports (
    id UUID PRIMARY KEY,
    scan_id UUID REFERENCES scans(id),
    format ENUM('pdf', 'json', 'csv'),
    file_path VARCHAR(255),
    generated_at TIMESTAMP DEFAULT NOW()
);
```

**Redis Cache Keys**:
- `scan:{id}:progress` - Real-time scan progress
- `user:{id}:history` - User's recent scans
- `ml:model:v1` - Cached ML model
- `rate_limit:{ip}` - API rate limiting

### 6. Integration Layer

**GitHub Actions**:
```yaml
# Auto-scan on PR
on: [pull_request]
  - Scan contracts in changed files
  - Comment findings on PR
  - Prevent merge if critical issues found
```

**Slack Bot**:
```python
@app.command("/scan")
async def scan_command(client, body):
    # Extract contract from message
    # Trigger BlockScope scan
    # Send results to Slack
```

**Etherscan Integration**:
```python
# Fetch verified contract source
# Auto-scan deployed contracts
# Track vulnerability trends
```

## 🔄 Data Flow

### Scanning Flow
```
1. User uploads contract
        ↓
2. API validates input
        ↓
3. Contract stored in DB
        ↓
4. Analysis Engine starts
        ├─ Static analysis
        ├─ Dynamic analysis
        └─ ML severity ranking
        ↓
5. Findings stored in DB
        ↓
6. Report generated
        ↓
7. User notified (email/UI)
```

### Authentication Flow
```
1. User enters credentials
        ↓
2. API validates & creates JWT
        ↓
3. JWT sent to frontend
        ↓
4. Frontend stores in localStorage
        ↓
5. All API requests include JWT
        ↓
6. API verifies JWT signature
```

## 🔐 Security Architecture

### Authentication
- JWT tokens (RS256 signing)
- Refresh tokens (short-lived)
- Rate limiting (100 req/min per IP)

### Authorization
- Role-based access control (RBAC)
- User owns their scans (scans.user_id = auth.user_id)
- Admin access to global stats

### Data Security
- Contracts encrypted at rest (AES-256)
- TLS/SSL for transport
- No plain-text storage
- Regular backups

## 📊 Performance Characteristics

| Metric | Target | Method |
|--------|--------|--------|
| Scan Time | <2s | Parallel analysis + caching |
| False Positive Rate | <5% | ML filtering |
| Throughput | 100+ scans/min | Async processing + queue |
| Uptime | 99.5% | Load balancing + monitoring |

## 🚀 Deployment Architecture

```
┌─────────────────────────────────────┐
│      User (Browser/CLI/API)        │
└────────────────┬────────────────────┘
                 │
        ┌────────▼────────┐
        │  Load Balancer  │
        │   (Nginx)       │
        └────────┬────────┘
                 │
        ┌────────┴────────┐
        │                 │
    ┌───▼──┐         ┌───▼──┐
    │Cont-1│         │Cont-2│ (Docker containers)
    │ API  │         │ API  │
    └───┬──┘         └───┬──┘
        │                 │
        └────────┬────────┘
                 │
        ┌────────┴────────┐
        │                 │
    ┌───▼──────┐   ┌─────▼──┐
    │PostgreSQL│   │ Redis  │
    │          │   │        │
    └──────────┘   └────────┘
```

**Containerization**:
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]

# frontend/Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## 📈 Scalability

**Horizontal Scaling**:
- Stateless API (can replicate)
- Async task queue (Celery/RQ)
- Database read replicas
- CDN for static assets

**Vertical Scaling**:
- Multi-worker Uvicorn
- Connection pooling
- Query optimization
- Cache layering

## 🔍 Monitoring & Observability

**Metrics**:
- API response time
- Scan completion rate
- False positive rate
- System resource usage

**Logging**:
- Structured JSON logs
- Centralized aggregation
- Error tracking (Sentry)

**Alerting**:
- Failed scans
- API errors (5xx)
- Database connection issues
- ML model performance degradation

---

**Next**: See [ROADMAP.md](ROADMAP.md) for implementation phases.
