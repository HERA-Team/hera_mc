"""Add RTPTaskProcessEvent table

Revision ID: 9d9af47e64c8
Revises: bb6db4d3fee6
Create Date: 2021-08-26 20:39:46.644181+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9d9af47e64c8"
down_revision = "bb6db4d3fee6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rtp_task_process_event",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("obsid", sa.BigInteger(), nullable=False),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column(
            "event",
            sa.Enum("started", "finished", "error", name="rtp_task_process_enum"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["obsid"],
            ["hera_obs.obsid"],
        ),
        sa.PrimaryKeyConstraint("time", "obsid", "task_name"),
    )


def downgrade():
    op.drop_table("rtp_task_process_event")
