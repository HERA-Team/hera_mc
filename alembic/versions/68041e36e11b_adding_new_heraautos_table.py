"""add HeraAutos table

Revision ID: 68041e36e11b
Revises: b022867d09e3
Create Date: 2019-12-30 20:56:04.518300+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "68041e36e11b"
down_revision = "b022867d09e3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hera_autos",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("antenna_number", sa.Integer(), nullable=False),
        sa.Column("antenna_feed_pol", sa.String(), nullable=False),
        sa.Column("measurement_type", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("time", "antenna_number", "antenna_feed_pol"),
    )
    # ### end Alembic commands ###


def downgrade():
    op.drop_table("hera_autos")
    # ### end Alembic commands ###
