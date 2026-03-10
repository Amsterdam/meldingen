"""add urgency to melding

Revision ID: 7a9f5e2e9d1b
Revises: 12443e52b756
Create Date: 2026-03-09 00:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a9f5e2e9d1b"
down_revision: str | None = "12443e52b756"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "melding",
        sa.Column("urgency", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "ck_melding_urgency",
        "melding",
        "urgency in (-1, 0, 1)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_melding_urgency", "melding", type_="check")
    op.drop_column("melding", "urgency")
