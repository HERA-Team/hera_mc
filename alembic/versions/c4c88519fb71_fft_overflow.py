"""fft_overflow

Revision ID: c4c88519fb71
Revises: 68041e36e11b
Create Date: 2020-06-12 22:52:29.674506+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c4c88519fb71"
down_revision = "68041e36e11b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "antenna_status", sa.Column("fft_overflow", sa.Boolean(), nullable=True)
    )


def downgrade():
    op.drop_column("antenna_status", "fft_overflow")
