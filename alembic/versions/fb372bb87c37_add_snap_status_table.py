"""add snap_status table

Revision ID: fb372bb87c37
Revises: 64c7a405e4c8
Create Date: 2019-03-19 22:32:13.745440+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "fb372bb87c37"
down_revision = "64c7a405e4c8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "snap_status",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.Column("node", sa.Integer(), nullable=True),
        sa.Column("snap_loc_num", sa.Integer(), nullable=True),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("psu_alert", sa.Boolean(), nullable=True),
        sa.Column("pps_count", sa.BigInteger(), nullable=True),
        sa.Column("fpga_temp", sa.Float(), nullable=True),
        sa.Column("uptime_cycles", sa.BigInteger(), nullable=True),
        sa.Column("last_programmed_time", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("time", "hostname"),
    )


def downgrade():
    op.drop_table("snap_status")
