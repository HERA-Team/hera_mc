"""add correlator and snap version info

Revision ID: 5fbb4d08569a
Revises: d208118c58d0
Create Date: 2019-04-02 18:51:00.603761+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5fbb4d08569a"
down_revision = "d208118c58d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "correlator_software_versions",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("package", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("time", "package"),
    )
    op.create_table(
        "snap_config_version",
        sa.Column("init_time", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("init_args", sa.String(), nullable=False),
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_hash"],
            ["correlator_config_file.config_hash"],
        ),
        sa.PrimaryKeyConstraint("init_time"),
    )


def downgrade():
    op.drop_table("snap_config_version")
    op.drop_table("correlator_software_versions")
