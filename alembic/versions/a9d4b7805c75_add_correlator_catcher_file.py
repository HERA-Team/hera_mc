"""add correlator catcher file

Revision ID: a9d4b7805c75
Revises: d81ba81442a3
Create Date: 2022-09-08 18:28:01.332525+00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a9d4b7805c75"
down_revision = "d81ba81442a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "correlator_catcher_file",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String()),
        sa.PrimaryKeyConstraint("time"),
    )


def downgrade():
    op.drop_table("correlator_catcher_file")
