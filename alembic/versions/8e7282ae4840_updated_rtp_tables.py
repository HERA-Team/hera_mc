"""updated rtp tables

Revision ID: 8e7282ae4840
Revises: e66c069eb92b
Create Date: 2017-08-13 18:06:40.892734+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8e7282ae4840"
down_revision = "e66c069eb92b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "rtp_process_record",
        sa.Column("hera_cal_git_hash", sa.String(length=64), nullable=False),
    )
    op.add_column(
        "rtp_process_record",
        sa.Column("hera_cal_git_version", sa.String(length=32), nullable=False),
    )
    op.add_column(
        "rtp_process_record",
        sa.Column("hera_qm_git_hash", sa.String(length=64), nullable=False),
    )
    op.add_column(
        "rtp_process_record",
        sa.Column("hera_qm_git_version", sa.String(length=32), nullable=False),
    )
    op.add_column(
        "rtp_process_record",
        sa.Column("pyuvdata_git_hash", sa.String(length=64), nullable=False),
    )
    op.add_column(
        "rtp_process_record",
        sa.Column("pyuvdata_git_version", sa.String(length=32), nullable=False),
    )
    op.alter_column("rtp_process_record", "git_hash", new_column_name="rtp_git_hash")
    op.alter_column(
        "rtp_process_record", "git_version", new_column_name="rtp_git_version"
    )


def downgrade():
    op.alter_column(
        "rtp_process_record", "rtp_git_version", new_column_name="git_version"
    )
    op.alter_column("rtp_process_record", "rtp_git_hash", new_column_name="git_hash")
    op.drop_column("rtp_process_record", "pyuvdata_git_version")
    op.drop_column("rtp_process_record", "pyuvdata_git_hash")
    op.drop_column("rtp_process_record", "hera_qm_git_version")
    op.drop_column("rtp_process_record", "hera_qm_git_hash")
    op.drop_column("rtp_process_record", "hera_cal_git_version")
    op.drop_column("rtp_process_record", "hera_cal_git_hash")
