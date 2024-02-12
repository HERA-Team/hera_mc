"""add_tag_to_hera_obs

Revision ID: d81ba81442a3
Revises: 1979f223bfbc
Create Date: 2022-08-08 19:23:16.626341+00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d81ba81442a3"
down_revision = "1979f223bfbc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("hera_obs", sa.Column("tag", sa.String(), nullable=True))


def downgrade():
    op.drop_column("hera_obs", "tag")
