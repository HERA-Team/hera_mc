"""Increase size of lib_files.filename

Revision ID: 3e86ac6195d8
Revises: 5b141f32ea38
Create Date: 2017-08-04 14:01:16.107299+00:00

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "3e86ac6195d8"
down_revision = "5b141f32ea38"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE lib_files ALTER COLUMN filename TYPE varchar(256);"))


def downgrade():
    conn = op.get_bind()
    conn.execute(
        text(
            "ALTER TABLE lib_files ALTER COLUMN filename TYPE varchar(32) USING substr(filename, 1, 32);"
        )
    )
