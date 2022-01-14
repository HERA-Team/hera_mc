"""add_ant_metric_indices

Revision ID: d2f22cbd4c5a
Revises: 5feda4ca9935
Create Date: 2022-01-14 22:49:15.514872+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d2f22cbd4c5a"
down_revision = "5feda4ca9935"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f("ix_ant_metrics_ant"), "ant_metrics", ["ant"], unique=False)
    op.create_index(
        op.f("ix_ant_metrics_metric"), "ant_metrics", ["metric"], unique=False
    )
    op.create_index(op.f("ix_ant_metrics_pol"), "ant_metrics", ["pol"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_ant_metrics_pol"), table_name="ant_metrics")
    op.drop_index(op.f("ix_ant_metrics_metric"), table_name="ant_metrics")
    op.drop_index(op.f("ix_ant_metrics_ant"), table_name="ant_metrics")
