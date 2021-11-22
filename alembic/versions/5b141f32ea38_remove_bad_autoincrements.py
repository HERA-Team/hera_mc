"""remove bad autoincrements

Revision ID: 5b141f32ea38
Revises: 4653b4902dc0
Create Date: 2017-07-27 22:51:11.172610+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence


# revision identifiers, used by Alembic.
revision = "5b141f32ea38"
down_revision = "4653b4902dc0"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute("ALTER TABLE hera_obs ALTER COLUMN obsid DROP DEFAULT;")
    conn.execute("ALTER TABLE lib_status ALTER COLUMN time DROP DEFAULT;")
    conn.execute("ALTER TABLE rtp_status ALTER COLUMN time DROP DEFAULT;")

    conn.execute("DROP SEQUENCE hera_obs_obsid_seq")
    conn.execute("DROP SEQUENCE lib_status_time_seq")
    conn.execute("DROP SEQUENCE rtp_status_time_seq")


def downgrade():
    op.execute(CreateSequence(Sequence("hera_obs_obsid_seq")))
    op.execute(CreateSequence(Sequence("lib_status_time_seq")))
    op.execute(CreateSequence(Sequence("rtp_status_time_seq")))

    op.alter_column(
        "hera_obs",
        "obsid",
        server_default=sa.text("nextval('hera_obs_obsid_seq'::regclass)"),
    )
    op.alter_column(
        "lib_status",
        "time",
        server_default=sa.text("nextval('lib_status_time_seq'::regclass)"),
    )
    op.alter_column(
        "rtp_status",
        "time",
        server_default=sa.text("nextval('rtp_status_time_seq'::regclass)"),
    )
