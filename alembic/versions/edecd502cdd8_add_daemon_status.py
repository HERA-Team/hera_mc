"""add daemon status


Revision ID: edecd502cdd8
Revises: a42f5c04610f
Create Date: 2019-07-10 22:50:31.279677+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "edecd502cdd8"
down_revision = "a42f5c04610f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "daemon_status",
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("hostname", sa.String(length=32), nullable=False),
        sa.Column("jd", sa.BigInteger(), nullable=False),
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("name", "hostname", "jd"),
    )


def downgrade():
    op.drop_table("daemon_status")
