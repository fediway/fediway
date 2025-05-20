"""create feeds table

Revision ID: 02c9f00fd297
Revises:
Create Date: 2025-03-25 16:54:49.771882

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "02c9f00fd297"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "feeds",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String, nullable=False),
        sa.Column("user_agent", sa.String, server_default="", nullable=False),
        sa.Column("ip", sa.String, nullable=True),
        sa.Column("name", sa.String, server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=True),
    )

    op.create_foreign_key(
        "fk_feeds_user_id", "feeds", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("feeds")
