"""add ant_status table

Revision ID: d208118c58d0
Revises: fb372bb87c37
Create Date: 2019-03-23 00:10:30.704936+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d208118c58d0"
down_revision = "fb372bb87c37"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "antenna_status",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("antenna_number", sa.Integer(), nullable=False),
        sa.Column("antenna_feed_pol", sa.String(), nullable=False),
        sa.Column("snap_hostname", sa.String(), nullable=True),
        sa.Column("snap_channel_number", sa.Integer(), nullable=True),
        sa.Column("adc_mean", sa.Float(), nullable=True),
        sa.Column("adc_rms", sa.Float(), nullable=True),
        sa.Column("adc_power", sa.Float(), nullable=True),
        sa.Column("pam_atten", sa.Integer(), nullable=True),
        sa.Column("pam_power", sa.Float(), nullable=True),
        sa.Column("eq_coeffs", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("time", "antenna_number", "antenna_feed_pol"),
    )


def downgrade():
    op.drop_table("antenna_status")
