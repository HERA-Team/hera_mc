"""add_corr_config_tables

Revision ID: 64c7a405e4c8
Revises: 9460cc78cb50
Create Date: 2018-11-27 03:22:19.564250+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "64c7a405e4c8"
down_revision = "9460cc78cb50"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "correlator_config_file",
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("config_hash"),
    )
    op.create_table(
        "correlator_config_command",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_hash"],
            ["correlator_config_file.config_hash"],
        ),
        sa.ForeignKeyConstraint(
            ["time", "command"],
            ["correlator_control_command.time", "correlator_control_command.command"],
        ),
        sa.PrimaryKeyConstraint("time", "command"),
    )
    op.create_table(
        "correlator_config_status",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_hash"],
            ["correlator_config_file.config_hash"],
        ),
        sa.PrimaryKeyConstraint("time"),
    )


def downgrade():
    op.drop_table("correlator_config_status")
    op.drop_table("correlator_config_command")
    op.drop_table("correlator_config_file")
