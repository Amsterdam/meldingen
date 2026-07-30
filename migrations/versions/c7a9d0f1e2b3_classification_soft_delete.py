"""classification soft delete

Revision ID: c7a9d0f1e2b3
Revises: b7e2c9a1f4d3
Create Date: 2026-07-28 00:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a9d0f1e2b3"
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
    # The partial index allowed a name to be reused after a soft-delete, so several rows may
    # share a name (all but at most one soft-deleted). A global unique constraint on name cannot
    # represent that, so the soft-deleted rows have to go first. Detach any meldingen still
    # pointing at them (the classification FK would otherwise block the delete); reverting
    # soft-delete inherently drops the "deleted but still shown on a melding" data.
    op.execute(
        sa.text(
            "UPDATE melding SET classification_id = NULL "
            "WHERE classification_id IN (SELECT id FROM classification WHERE deleted_at IS NOT NULL)"
        )
    )
    op.execute(sa.text("DELETE FROM classification WHERE deleted_at IS NOT NULL"))
    op.create_unique_constraint("classification_name", "classification", ["name"])
    op.drop_column("classification", "deleted_at")
