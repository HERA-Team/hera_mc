"""add part_rosetta table

Revision ID: 7463268309ab
Revises: c4c88519fb71
Create Date: 2020-08-19 22:15:42.200290+00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7463268309ab"
down_revision = "c4c88519fb71"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "part_rosetta",
        sa.Column("hpn", sa.String(length=64), nullable=False),
        sa.Column("syspn", sa.String(length=64), nullable=False),
        sa.Column("start_gpstime", sa.BigInteger(), nullable=False),
        sa.Column("stop_gpstime", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("syspn", "start_gpstime"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("part_rosetta")
    # ### end Alembic commands ###
