"""more_antenna_stats

Revision ID: 50c966c5427a
Revises: edecd502cdd8
Create Date: 2019-07-19 19:59:08.371361+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "50c966c5427a"
down_revision = "edecd502cdd8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("antenna_status", sa.Column("fem_current", sa.Float(), nullable=True))
    op.add_column("antenna_status", sa.Column("fem_id", sa.String(), nullable=True))
    op.add_column("antenna_status", sa.Column("fem_temp", sa.Float(), nullable=True))
    op.add_column("antenna_status", sa.Column("fem_voltage", sa.Float(), nullable=True))
    op.add_column("antenna_status", sa.Column("histogram", sa.String(), nullable=True))
    op.add_column(
        "antenna_status", sa.Column("histogram_bin_centers", sa.String(), nullable=True)
    )
    op.add_column("antenna_status", sa.Column("pam_current", sa.Float(), nullable=True))
    op.add_column("antenna_status", sa.Column("pam_id", sa.String(), nullable=True))
    op.add_column("antenna_status", sa.Column("pam_voltage", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("antenna_status", "pam_voltage")
    op.drop_column("antenna_status", "pam_id")
    op.drop_column("antenna_status", "pam_current")
    op.drop_column("antenna_status", "histogram_bin_centers")
    op.drop_column("antenna_status", "histogram")
    op.drop_column("antenna_status", "fem_voltage")
    op.drop_column("antenna_status", "fem_temp")
    op.drop_column("antenna_status", "fem_id")
    op.drop_column("antenna_status", "fem_current")
