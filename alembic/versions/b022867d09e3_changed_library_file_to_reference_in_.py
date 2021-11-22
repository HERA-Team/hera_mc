"""changed library_file to reference in part_info

Revision ID: b022867d09e3
Revises: e83aa47e530b
Create Date: 2019-11-25 20:34:47.384076+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b022867d09e3"
down_revision = "63b625cf7b06"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("part_info", "library_file", new_column_name="reference")


def downgrade():
    op.alter_column("part_info", "reference", new_column_name="library_file")
