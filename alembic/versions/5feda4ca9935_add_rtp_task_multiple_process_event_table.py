"""Add rtp_task_multiple_process_event table

Revision ID: 5feda4ca9935
Revises: 9d9af47e64c8
Create Date: 2021-09-30 16:22:30.118641+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5feda4ca9935"
down_revision = "9d9af47e64c8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rtp_task_multiple_process_event",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("obsid_start", sa.BigInteger(), nullable=False),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column(
            "event",
            sa.Enum(
                "started", "finished", "error", name="rtp_task_multiple_process_enum"
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["obsid_start"],
            ["hera_obs.obsid"],
        ),
        sa.PrimaryKeyConstraint("time", "obsid_start", "task_name"),
    )


def downgrade():
    op.drop_table("rtp_task_multiple_process_event")
