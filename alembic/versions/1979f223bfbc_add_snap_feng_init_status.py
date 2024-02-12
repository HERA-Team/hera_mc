"""add_snap_feng_init_status

Revision ID: 1979f223bfbc
Revises: 67e70aa050ed
Create Date: 2022-08-02 23:18:16.685003+00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1979f223bfbc"
down_revision = "67e70aa050ed"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "snap_feng_init_status",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("time", "hostname"),
    )


def downgrade():
    op.drop_table("snap_feng_init_status")
