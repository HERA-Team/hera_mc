"""Add task_name column to RTPProcessEvent

Revision ID: 72037abf4fcf
Revises: bb6db4d3fee6
Create Date: 2021-08-24 23:09:13.750545+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '72037abf4fcf'
down_revision = 'bb6db4d3fee6'
branch_labels = None
depends_on = None


def upgrade():
    # drop primary key constraint
    op.drop_constraint("rtp_process_event_pkey", "rtp_process_event", type_="primary")
    # add new column
    op.add_column('rtp_process_event', sa.Column('task_name', sa.String(), nullable=False))
    # make bogus task for existing rows
    op.execute("UPDATE rtp_process_event SET task_name = 'TASK'")
    # make new primary key
    op.create_primary_key("rtp_process_event_pkey", "rtp_process_event", ["time", "obsid", "task_name"])

def downgrade():
    # undo primary key change
    op.drop_constraint("rtp_process_event_pkey", "rtp_process_event", type_="primary")
    # drop column
    op.drop_column('rtp_process_event', 'task_name')
    # make new primary key
    op.create_primary_key("rtp_process_event_pkey", "rtp_process_event", ["time", "obsid"])
