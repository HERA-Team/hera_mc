"""add_time_views

Revision ID: 74e327e433c9
Revises: 64c7a405e4c8
Create Date: 2019-02-15 21:52:55.720955+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import hera_mc

# revision identifiers, used by Alembic.
revision = '74e327e433c9'
down_revision = '64c7a405e4c8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_view(hera_mc.observations.HeraObsView)


def downgrade():
    op.drop_view(hera_mc.observations.HeraObsView)
