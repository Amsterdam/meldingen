"""merge reply notes and classifier result

Revision ID: f42c84a1b866
Revises: 45b641ffc27f, 525dd29f937d
Create Date: 2026-11-11 15:04:18.691131

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "f42c84a1b866"
down_revision: str | None = ("45b641ffc27f", "525dd29f937d")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
