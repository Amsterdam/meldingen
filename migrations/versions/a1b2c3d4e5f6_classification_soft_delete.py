"""classification soft delete

Revision ID: a1b2c3d4e5f6
Revises: b7e2c9a1f4d3
Create Date: 2026-07-28 00:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "b7e2c9a1f4d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("classification", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    # Replace the plain unique constraint on name with a partial unique index so a name is
    # only unique among non-deleted classifications and can be reused after deletion.
    op.drop_constraint("classification_name", "classification", type_="unique")
    op.create_index(
        "uq_classification_name_active",
        "classification",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_classification_name_active", table_name="classification")
    op.create_unique_constraint("classification_name", "classification", ["name"])
    op.drop_column("classification", "deleted_at")
