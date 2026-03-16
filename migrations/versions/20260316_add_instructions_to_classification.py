"""
Add instructions field to classification
"""

# Alembic revision identifiers, used by Alembic.
revision = "20260316_add_instructions_to_classification"
down_revision = "eb1f60f8afbd"
branch_labels = None
depends_on = None
import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column("classification", sa.Column("instructions", sa.String(), nullable=True))


def downgrade():
    op.drop_column("classification", "instructions")
