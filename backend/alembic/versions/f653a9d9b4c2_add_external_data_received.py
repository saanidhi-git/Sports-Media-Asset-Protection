"""add_external_data_received

Revision ID: f653a9d9b4c2
Revises: e86b38cdd8e5
Create Date: 2026-04-26 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f653a9d9b4c2'
down_revision: Union[str, Sequence[str], None] = 'e86b38cdd8e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('scan_jobs', sa.Column('external_data_received', sa.Boolean(), nullable=True))
    # Update existing rows to False
    op.execute("UPDATE scan_jobs SET external_data_received = False")
    # Make it non-nullable if desired, but for safety with existing data we start nullable
    # or just set a server default
    op.alter_column('scan_jobs', 'external_data_received', server_default=sa.text('false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('scan_jobs', 'external_data_received')
