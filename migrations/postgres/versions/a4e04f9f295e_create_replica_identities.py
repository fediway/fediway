"""create replica identities

Revision ID: a4e04f9f295e
Revises: 99f2eb6aca5b
Create Date: 2025-04-17 01:19:46.928043

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4e04f9f295e"
down_revision: Union[str, None] = "99f2eb6aca5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "accounts",
    "statuses",
    "status_stats",
    "follows",
    "mentions",
    "favourites",
    "tags",
    "statuses_tags",
]


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} REPLICA IDENTITY FULL;")


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} REPLICA IDENTITY DEFAULT;")
