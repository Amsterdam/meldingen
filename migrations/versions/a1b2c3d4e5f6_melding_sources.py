"""melding sources

Revision ID: a1b2c3d4e5f6
Revises: 6c2b254579da
Create Date: 2026-04-29 13:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "6c2b254579da"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.add_column("melding", sa.Column("source_id", sa.Integer(), nullable=True))
    op.create_foreign_key(None, "melding", "source", ["source_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(None, "melding", type_="foreignkey")
    op.drop_column("melding", "source_id")
    op.drop_table("source")
