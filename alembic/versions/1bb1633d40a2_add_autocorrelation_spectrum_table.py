"""add autocorrelation spectrum table

Revision ID: 1bb1633d40a2
Revises: a9d4b7805c75
Create Date: 2022-10-31 20:16:25.669383+00:00

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1bb1633d40a2"
down_revision = "a9d4b7805c75"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hera_auto_spectrum",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("antenna_number", sa.Integer(), nullable=False),
        sa.Column("antenna_feed_pol", sa.String(), nullable=False),
        sa.Column(
            "spectrum", postgresql.ARRAY(sa.REAL(), dimensions=1), nullable=False
        ),
        sa.PrimaryKeyConstraint("time", "antenna_number", "antenna_feed_pol"),
    )


def downgrade():
    op.drop_table("hera_auto_spectrum")
