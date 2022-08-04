"""redo correlator interface

Revision ID: 1bf3ac824a22
Revises: c66b6b222bde
Create Date: 2022-07-13 23:40:03.485505+00:00

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1bf3ac824a22"
down_revision = "c66b6b222bde"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "array_signal_source",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("time"),
    )
    op.create_table(
        "correlator_component_event_time",
        sa.Column("component", sa.String(), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("time", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("component", "event", "time"),
    )


def downgrade():
    op.drop_table("correlator_component_event_time")
    op.drop_table("array_signal_source")
