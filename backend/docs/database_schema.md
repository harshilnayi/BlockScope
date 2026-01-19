# BlockScope Database Schema

## Table: scans

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Unique scan identifier |
| contract_name | String | Name of the smart contract |
| source_code | Text | Solidity source code |
| vulnerabilities_count | Integer | Total vulnerabilities detected |
| severity_breakdown | JSON | Count per severity |
| overall_score | Float | Risk score |
| summary | Text | Scan summary |
| findings | JSON | Detailed vulnerability list |
| scanned_at | Timestamp | Scan execution time |

## Table: findings (if enabled)

| Column | Type |
|--------|------|
| id | Integer |
| scan_id | FK → scans.id |
| type | String |
| severity | String |
| description | Text |
| line_number | Integer |
