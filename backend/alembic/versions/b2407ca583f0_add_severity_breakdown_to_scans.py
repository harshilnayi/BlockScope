"""add severity_breakdown to scans

Revision ID: b2407ca583f0
Revises: 48ef6f0801a4
Create Date: 2026-01-19 15:30:53.686473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2407ca583f0'
down_revision: Union[str, Sequence[str], None] = '48ef6f0801a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'scans',
        sa.Column('severity_breakdown', sa.JSON(), server_default='{}', nullable=False)
    )
    op.alter_column('scans', 'severity_breakdown', server_default=None)


def downgrade():
    op.drop_column('scans', 'severity_breakdown')