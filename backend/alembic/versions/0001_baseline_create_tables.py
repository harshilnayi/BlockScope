"""baseline: create scans and findings tables

Revision ID: 0001_baseline
Revises: -
Create Date: 2026-05-12

Baseline migration that creates the schema matching the current
SQLAlchemy models.  If you are applying this to a database that
already has the tables, stamp instead of upgrading::

    alembic stamp 0001_baseline
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the scans and findings tables."""

    # ── scans table ──────────────────────────────────────────────────
    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contract_name", sa.String(255), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), server_default="completed"),
        sa.Column("vulnerabilities_count", sa.Integer(), server_default="0"),
        sa.Column("severity_breakdown", sa.JSON(), nullable=True),
        sa.Column("overall_score", sa.Integer(), server_default="100"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("scanned_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
        ),
    )
    op.create_index("ix_scans_id", "scans", ["id"])

    # ── findings table ───────────────────────────────────────────────
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "scan_id",
            sa.Integer(),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_findings_id", "findings", ["id"])
    op.create_index("ix_findings_scan_id", "findings", ["scan_id"])
    op.create_index("ix_findings_rule_id", "findings", ["rule_id"])
    op.create_index("ix_findings_severity", "findings", ["severity"])


def downgrade() -> None:
    """Drop findings and scans tables."""
    op.drop_table("findings")
    op.drop_table("scans")
