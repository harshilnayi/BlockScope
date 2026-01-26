"""fix findings default

Revision ID: b1f9ea63a7ab
Revises: dfc2cc892ab9
Create Date: 2026-01-19 15:41:09.924106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f9ea63a7ab'
down_revision: Union[str, Sequence[str], None] = 'dfc2cc892ab9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'scans',
        sa.Column('findings', sa.JSON(), server_default='[]', nullable=False)
    )

def downgrade():
    op.drop_column('scans', 'findings')

