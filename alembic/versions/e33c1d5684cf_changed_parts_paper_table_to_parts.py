"""changed parts_paper table to parts

Revision ID: e33c1d5684cf
Revises: 3d3c72ecbc0d
Create Date: 2018-01-30 01:02:58.347378+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e33c1d5684cf"
down_revision = "3d3c72ecbc0d"
branch_labels = None
depends_on = None

# Hand-edited -- see http://petegraham.co.uk/rename-postgres-table-with-alembic/


def upgrade():
    # ### commands hand-edited to only rename_table ###
    op.rename_table("parts_paper", "parts")
    # ### end Alembic commands ###


def downgrade():
    # ### commands hand-edited to apply rename_table ###
    op.rename_table("parts", "parts_paper")
    # ### end Alembic commands ###
