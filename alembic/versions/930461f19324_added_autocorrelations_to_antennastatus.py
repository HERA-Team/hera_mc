"""added autocorrelations to antennastatus

Revision ID: 930461f19324
Revises: 50c966c5427a
Create Date: 2019-08-22 20:56:03.992054+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '930461f19324'
down_revision = '50c966c5427a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('antenna_status', sa.Column('autocorrelation', sa.String(), nullable=True))


def downgrade():
    op.drop_column('antenna_status', 'autocorrelation')
