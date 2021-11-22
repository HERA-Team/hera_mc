"""add node control

Revision ID: 40a641ef2f52
Revises: a3d144cdc527
Create Date: 2018-08-30 20:02:26.339879+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "40a641ef2f52"
down_revision = "a3d144cdc527"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "node_power_command",
        sa.Column("time", sa.BigInteger(), nullable=False),
        sa.Column("node", sa.Integer(), nullable=False),
        sa.Column("part", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("time", "node", "part"),
    )


def downgrade():
    op.drop_table("node_power_command")
