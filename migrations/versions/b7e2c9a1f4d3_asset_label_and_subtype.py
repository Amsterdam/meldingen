"""asset label and subtype

Revision ID: b7e2c9a1f4d3
Revises: c3f1a2b4d5e6
Create Date: 2026-07-02 00:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2c9a1f4d3"
down_revision: str | None = "c3f1a2b4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # New non-nullable columns. Use a temporary server_default so existing rows
    # get a value, then drop the default to keep the model definition clean.
    op.add_column("asset", sa.Column("label", sa.String(), nullable=False, server_default=""))
    op.add_column("asset", sa.Column("subtype", sa.String(), nullable=False, server_default=""))
    op.alter_column("asset", "label", server_default=None)
    op.alter_column("asset", "subtype", server_default=None)


def downgrade() -> None:
    op.drop_column("asset", "subtype")
    op.drop_column("asset", "label")
