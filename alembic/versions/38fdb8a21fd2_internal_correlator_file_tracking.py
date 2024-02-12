"""internal correlator file tracking

Revision ID: 38fdb8a21fd2
Revises: 1bb1633d40a2
Create Date: 2023-01-23 19:21:58.068257+00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "38fdb8a21fd2"
down_revision = "1bb1633d40a2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "correlator_file_eod",
        sa.Column("jd", sa.BigInteger(), nullable=False),
        sa.Column("time_start", sa.BigInteger(), nullable=True),
        sa.Column("time_converted", sa.BigInteger(), nullable=True),
        sa.Column("time_uploaded", sa.BigInteger(), nullable=True),
        sa.Column("time_launch_failed", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("jd"),
    )
    op.create_table(
        "correlator_file_queues",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("queue", sa.String(), nullable=False),
        sa.Column("length", sa.Integer(), nullable=True),
        sa.Column("oldest_entry", sa.String(), nullable=True),
        sa.Column("newest_entry", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("time", "queue"),
    )


def downgrade():
    op.drop_table("correlator_file_queues")
    op.drop_table("correlator_file_eod")
