"""add_nodes

Revision ID: a3d144cdc527
Revises: e33c1d5684cf
Create Date: 2018-08-08 23:49:22.439468+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a3d144cdc527"
down_revision = "e33c1d5684cf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "node_power_status",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("node", sa.Integer(), nullable=False),
        sa.Column("snap_relay_powered", sa.Boolean(), nullable=False),
        sa.Column("snap0_powered", sa.Boolean(), nullable=False),
        sa.Column("snap1_powered", sa.Boolean(), nullable=False),
        sa.Column("snap2_powered", sa.Boolean(), nullable=False),
        sa.Column("snap3_powered", sa.Boolean(), nullable=False),
        sa.Column("fem_powered", sa.Boolean(), nullable=False),
        sa.Column("pam_powered", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("time", "node"),
    )
    op.create_table(
        "node_sensor",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("node", sa.Integer(), nullable=False),
        sa.Column("top_sensor_temp", sa.Float(), nullable=True),
        sa.Column("middle_sensor_temp", sa.Float(), nullable=True),
        sa.Column("bottom_sensor_temp", sa.Float(), nullable=True),
        sa.Column("humidity_sensor_temp", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("time", "node"),
    )


def downgrade():
    op.drop_table("node_sensor")
    op.drop_table("node_power_status")
