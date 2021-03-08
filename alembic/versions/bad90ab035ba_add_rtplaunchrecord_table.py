"""Add RTPLaunchRecord table

Revision ID: bad90ab035ba
Revises: 77c082c87844
Create Date: 2021-03-08 19:16:44.611253+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "bad90ab035ba"
down_revision = "77c082c87844"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rtp_launch_record",
        sa.Column("obsid", sa.BigInteger(), nullable=False),
        sa.Column("submitted_time", sa.BigInteger(), nullable=True),
        sa.Column("rtp_attempts", sa.BigInteger(), nullable=False),
        sa.Column("jd", sa.BigInteger(), nullable=False),
        sa.Column("obs_tag", sa.String(length=128), nullable=False),
        sa.Column("filename", sa.String(length=128), nullable=False),
        sa.Column("prefix", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["obsid"],
            ["hera_obs.obsid"],
        ),
        sa.PrimaryKeyConstraint("obsid"),
    )


def downgrade():
    op.drop_table("rtp_launch_record")
