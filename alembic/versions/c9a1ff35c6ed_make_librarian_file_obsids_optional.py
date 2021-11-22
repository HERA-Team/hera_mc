"""Make Librarian file obsids optional.

Revision ID: c9a1ff35c6ed
Revises: f29adafca107
Create Date: 2017-12-15 18:50:37.889271+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "c9a1ff35c6ed"
down_revision = "f29adafca107"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("lib_files", "obsid", existing_type=sa.BIGINT(), nullable=True)


def downgrade():
    # NOTE this likely won't work unless we delete the rows that actually have
    # null obsids.
    op.alter_column("lib_files", "obsid", existing_type=sa.BIGINT(), nullable=False)
