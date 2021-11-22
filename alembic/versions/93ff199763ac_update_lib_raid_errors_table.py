"""update lib_raid_errors table

Revision ID: 93ff199763ac
Revises: b1063869f198
Create Date: 2017-07-27 00:13:29.765073+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence


# revision identifiers, used by Alembic.
revision = "93ff199763ac"
down_revision = "b1063869f198"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("lib_raid_errors_pkey", "lib_raid_errors", type_="primary")

    op.execute(CreateSequence(Sequence("lib_raid_errors_id_seq")))
    op.add_column(
        "lib_raid_errors",
        sa.Column(
            "id",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("nextval('lib_raid_errors_id_seq'::regclass)"),
        ),
    )

    op.create_primary_key(
        "lib_raid_errors_pkey",
        "lib_raid_errors",
        [
            "id",
        ],
    )
    # ### end Alembic commands ###


def downgrade():
    op.drop_constraint("lib_raid_errors_pkey", "lib_raid_errors", type_="primary")
    op.drop_column("lib_raid_errors", "id")

    op.create_primary_key(
        "lib_raid_errors_pkey", "lib_raid_errors", ["time", "hostname", "disk"]
    )

    # ### end Alembic commands ###
