"""add correlator control

Revision ID: 9460cc78cb50
Revises: 40a641ef2f52
Create Date: 2018-11-01 17:34:57.968829+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9460cc78cb50"
down_revision = "40a641ef2f52"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "correlator_control_command",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("time", "command"),
    )
    op.create_table(
        "correlator_control_state",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("state_type", sa.String(), nullable=False),
        sa.Column("state", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("time", "state_type"),
    )
    op.create_table(
        "correlator_take_data_arguments",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("starttime_sec", sa.BigInteger(), nullable=False),
        sa.Column("starttime_ms", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("acclen_spectra", sa.Integer(), nullable=False),
        sa.Column("integration_time", sa.Float(), nullable=False),
        sa.Column("tag", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["time", "command"],
            ["correlator_control_command.time", "correlator_control_command.command"],
        ),
        sa.PrimaryKeyConstraint("time", "command"),
    )


def downgrade():
    op.drop_table("correlator_take_data_arguments")
    op.drop_table("correlator_control_state")
    op.drop_table("correlator_control_command")
