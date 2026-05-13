"""add performance indexes to scans and findings

Revision ID: 0002_add_indexes
Revises: 0001_baseline
Create Date: 2026-05-12

Adds indexes to support the most common query patterns:

- ``GET /scans`` orders by ``scanned_at DESC`` → idx_scans_scanned_at
- Dashboard filtering by score → idx_scans_overall_score
- Status filtering → idx_scans_status
- Contract name search → idx_scans_contract_name
- Findings per-scan-by-severity queries → idx_findings_scan_severity
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_indexes"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create performance indexes."""
    # scans table
    op.create_index("idx_scans_scanned_at", "scans", [sa.text("scanned_at DESC")])
    op.create_index("idx_scans_created_at", "scans", ["created_at"])
    op.create_index("idx_scans_overall_score", "scans", ["overall_score"])
    op.create_index("idx_scans_status", "scans", ["status"])
    op.create_index("idx_scans_contract_name", "scans", ["contract_name"])

    # findings table — composite index for per-scan severity queries
    op.create_index("idx_findings_scan_severity", "findings", ["scan_id", "severity"])


def downgrade() -> None:
    """Drop performance indexes."""
    op.drop_index("idx_findings_scan_severity", table_name="findings")
    op.drop_index("idx_scans_contract_name", table_name="scans")
    op.drop_index("idx_scans_status", table_name="scans")
    op.drop_index("idx_scans_overall_score", table_name="scans")
    op.drop_index("idx_scans_created_at", table_name="scans")
    op.drop_index("idx_scans_scanned_at", table_name="scans")
