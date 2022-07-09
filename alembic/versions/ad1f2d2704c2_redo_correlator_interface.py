"""redo_correlator_interface

Revision ID: ad1f2d2704c2
Revises: c66b6b222bde
Create Date: 2022-07-08 23:08:02.199668+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ad1f2d2704c2"
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
        sa.Column("component_event", sa.String(), nullable=False),
        sa.Column("time", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("component_event", "time"),
    )


def downgrade():
    op.drop_table("correlator_component_event_time")
    op.drop_table("array_signal_source")
