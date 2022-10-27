"""add autocorrelation spectrum table

Revision ID: 387d68a970aa
Revises: a9d4b7805c75
Create Date: 2022-10-27 22:23:07.640796+00:00

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "387d68a970aa"
down_revision = "a9d4b7805c75"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hera_auto_spectrum",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("antenna_number", sa.Integer(), nullable=False),
        sa.Column("antenna_feed_pol", sa.String(), nullable=False),
        sa.Column("spectrum", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.PrimaryKeyConstraint("time", "antenna_number", "antenna_feed_pol"),
    )


def downgrade():
    op.drop_table("hera_auto_spectrum")
