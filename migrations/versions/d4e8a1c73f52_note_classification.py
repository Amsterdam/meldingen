"""note classification

Revision ID: d4e8a1c73f52
Revises: 75ab04c1868a
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e8a1c73f52"
down_revision: str | None = "75ab04c1868a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: only the note that records a reclassification references a classification, every
    # note written by hand leaves it empty.
    op.add_column("note", sa.Column("classification_id", sa.Integer(), nullable=True))
    op.create_foreign_key("note_classification_id_fkey", "note", "classification", ["classification_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("note_classification_id_fkey", "note", type_="foreignkey")
    op.drop_column("note", "classification_id")
