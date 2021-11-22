"""add antenna status columns

Revision ID: e83aa47e530b
Revises: 50c966c5427a
Create Date: 2019-11-03 17:40:45.108617+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e83aa47e530b"
down_revision = "50c966c5427a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("antenna_status", sa.Column("fem_imu_phi", sa.Float(), nullable=True))
    op.add_column(
        "antenna_status", sa.Column("fem_imu_theta", sa.Float(), nullable=True)
    )
    op.add_column(
        "antenna_status", sa.Column("fem_lna_power", sa.Boolean(), nullable=True)
    )
    op.add_column("antenna_status", sa.Column("fem_switch", sa.String(), nullable=True))


def downgrade():
    op.drop_column("antenna_status", "fem_switch")
    op.drop_column("antenna_status", "fem_lna_power")
    op.drop_column("antenna_status", "fem_imu_theta")
    op.drop_column("antenna_status", "fem_imu_phi")
