"""Update RTP status table

Revision ID: e1ca8599e705
Revises: 8e7282ae4840
Create Date: 2017-08-15 21:03:28.459132+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1ca8599e705'
down_revision = '8e7282ae4840'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('rtp_status_pkey', 'rtp_status', type_='primary')
    op.add_column('rtp_status', sa.Column('hostname', sa.String(length=32)))
    op.create_primary_key('rtp_status_pkey', 'rtp_status', ['time', 'hostname'])


def downgrade():
    op.drop_constraint('rtp_status_pkey', 'rtp_status', type_='primary')
    op.drop_column('rtp_status', 'hostname')
    op.create_primary_key('rtp_status_pkey', 'rtp_status', ['time', ])
