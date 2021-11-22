"""added apriori_antenna table

Revision ID: a42f5c04610f
Revises: 5fbb4d08569a
Create Date: 2019-04-16 03:08:40.531643+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a42f5c04610f"
down_revision = "5fbb4d08569a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "apriori_antenna",
        sa.Column("antenna", sa.Text(), nullable=False),
        sa.Column("start_gpstime", sa.BigInteger(), nullable=False),
        sa.Column("stop_gpstime", sa.BigInteger()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("antenna", "start_gpstime"),
    )


def downgrade():
    op.drop_table("apriori_antenna")
