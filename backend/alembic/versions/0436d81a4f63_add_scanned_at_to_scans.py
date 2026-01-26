"""add scanned_at to scans

Revision ID: 0436d81a4f63
Revises: b1f9ea63a7ab
Create Date: 2026-01-19 15:47:35.019214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0436d81a4f63'
down_revision: Union[str, Sequence[str], None] = 'b1f9ea63a7ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'scans',
        sa.Column('scanned_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )
    op.alter_column('scans', 'scanned_at', server_default=None)


def downgrade():
    op.drop_column('scans', 'scanned_at')
