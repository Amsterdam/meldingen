"""add required error message to form

Revision ID: c5fa7f605c3c
Revises: c8c2fdecdd9a
Create Date: 2025-08-12 13:56:01.528123

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5fa7f605c3c"
down_revision: str | None = "c8c2fdecdd9a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "form_io_component",
        sa.Column("required_error_message", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("form_io_component", "required_error_message")
