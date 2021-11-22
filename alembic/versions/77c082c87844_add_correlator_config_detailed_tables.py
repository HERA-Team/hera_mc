"""add correlator config detailed tables

Revision ID: 77c082c87844
Revises: 7463268309ab
Create Date: 2021-01-15 21:26:15.737527+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "77c082c87844"
down_revision = "7463268309ab"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "correlator_config_active_snap",
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_hash"],
            ["correlator_config_file.config_hash"],
        ),
        sa.PrimaryKeyConstraint("config_hash", "hostname"),
    )
    op.create_table(
        "correlator_config_input_index",
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.Column("correlator_index", sa.Integer(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.Column("antenna_index_position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_hash"],
            ["correlator_config_file.config_hash"],
        ),
        sa.PrimaryKeyConstraint("config_hash", "correlator_index"),
    )
    op.create_table(
        "correlator_config_params",
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.Column("parameter", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_hash"],
            ["correlator_config_file.config_hash"],
        ),
        sa.PrimaryKeyConstraint("config_hash", "parameter"),
    )
    op.create_table(
        "correlator_config_phase_switch_index",
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.Column("phase_switch_index", sa.Integer(), nullable=False),
        sa.Column("antpol_index_position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_hash"],
            ["correlator_config_file.config_hash"],
        ),
        sa.PrimaryKeyConstraint("config_hash", "hostname", "phase_switch_index"),
    )


def downgrade():
    op.drop_table("correlator_config_phase_switch_index")
    op.drop_table("correlator_config_params")
    op.drop_table("correlator_config_input_index")
    op.drop_table("correlator_config_active_snap")
