"""more snap info

Revision ID: 67e70aa050ed
Revises: 1bf3ac824a22
Create Date: 2022-07-19 17:46:45.063811+00:00

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "67e70aa050ed"
down_revision = "1bf3ac824a22"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "snap_input",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.Column("snap_channel_number", sa.Integer(), nullable=False),
        sa.Column("antenna_number", sa.Integer(), nullable=True),
        sa.Column("antenna_feed_pol", sa.String(), nullable=True),
        sa.Column("snap_input", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["time", "hostname"],
            ["snap_status.time", "snap_status.hostname"],
        ),
        sa.PrimaryKeyConstraint("time", "hostname", "snap_channel_number"),
    )

    op.add_column(
        "snap_status", sa.Column("is_programmed", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "snap_status", sa.Column("adc_is_configured", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "snap_status", sa.Column("is_initialized", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "snap_status", sa.Column("dest_is_configured", sa.Boolean(), nullable=True)
    )
    op.add_column("snap_status", sa.Column("version", sa.String(), nullable=True))
    op.add_column("snap_status", sa.Column("sample_rate", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("snap_status", "sample_rate")
    op.drop_column("snap_status", "version")
    op.drop_column("snap_status", "dest_is_configured")
    op.drop_column("snap_status", "is_initialized")
    op.drop_column("snap_status", "adc_is_configured")
    op.drop_column("snap_status", "is_programmed")

    op.drop_table("snap_input")
