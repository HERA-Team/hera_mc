"""added new apriori_antenna table

Revision ID: 6496fb7766e3
Revises: 5fbb4d08569a
Create Date: 2019-04-12 02:05:04.624693+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6496fb7766e3'
down_revision = '5fbb4d08569a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('apriori_antenna',
    sa.Column('antenna', sa.Text(), nullable=False),
    sa.Column('start_gpstime', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('antenna', 'start_gpstime')
    )


def downgrade():
    op.drop_table('apriori_antenna')
