"""add_rtp_tracking_tables

Revision ID: bb6db4d3fee6
Revises: 77c082c87844
Create Date: 2021-02-18 21:10:33.076138+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "bb6db4d3fee6"
down_revision = "bad90ab035ba"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rtp_task_jobid",
        sa.Column("obsid", sa.BigInteger(), nullable=False),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("start_time", sa.BigInteger(), nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["obsid"],
            ["hera_obs.obsid"],
        ),
        sa.PrimaryKeyConstraint("obsid", "task_name", "start_time"),
    )
    op.create_table(
        "rtp_task_multiple_jobid",
        sa.Column("obsid_start", sa.BigInteger(), nullable=False),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("start_time", sa.BigInteger(), nullable=False),
        sa.Column("job_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["obsid_start"],
            ["hera_obs.obsid"],
        ),
        sa.PrimaryKeyConstraint("obsid_start", "task_name", "start_time"),
    )
    op.create_table(
        "rtp_task_multiple_resource_record",
        sa.Column("obsid_start", sa.BigInteger(), nullable=False),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("start_time", sa.BigInteger(), nullable=False),
        sa.Column("stop_time", sa.BigInteger(), nullable=False),
        sa.Column("max_memory", sa.Float(), nullable=True),
        sa.Column("avg_cpu_load", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["obsid_start"],
            ["hera_obs.obsid"],
        ),
        sa.PrimaryKeyConstraint("obsid_start", "task_name"),
    )
    op.create_table(
        "rtp_task_multiple_track",
        sa.Column("obsid_start", sa.BigInteger(), nullable=False),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("obsid", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["obsid"],
            ["hera_obs.obsid"],
        ),
        sa.ForeignKeyConstraint(
            ["obsid_start"],
            ["hera_obs.obsid"],
        ),
        sa.PrimaryKeyConstraint("obsid_start", "task_name", "obsid"),
    )


def downgrade():
    op.drop_table("rtp_task_multiple_track")
    op.drop_table("rtp_task_multiple_resource_record")
    op.drop_table("rtp_task_multiple_jobid")
    op.drop_table("rtp_task_jobid")
