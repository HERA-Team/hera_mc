"""add cm_version table

Revision ID: c0985153bf41
Revises: 8e7282ae4840
Create Date: 2017-08-19 01:57:48.642443+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c0985153bf41"
down_revision = "8e7282ae4840"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cm_version",
        sa.Column("update_time", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("git_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("update_time"),
    )
    op.drop_table("host_status")
    # ### end Alembic commands ###


def downgrade():
    op.drop_table("cm_version")
    # ### end Alembic commands ###
