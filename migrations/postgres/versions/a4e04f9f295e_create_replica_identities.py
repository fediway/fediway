"""create replica identities

Revision ID: a4e04f9f295e
Revises: 99f2eb6aca5b
Create Date: 2025-04-17 01:19:46.928043

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4e04f9f295e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "account_conversations",
    "account_domain_blocks",
    "account_notes",
    "account_pins",
    "accounts",
    "accounts_tags",
    "blocks",
    "bookmarks",
    "conversation_mutes",
    "conversations",
    "favourites",
    "featured_tags",
    "follow_recommendation_mutes",
    "follow_recommendation_suppressions",
    "follow_requests",
    "follows",
    "invites",
    "list_accounts",
    "lists",
    "media_attachments",
    "mentions",
    "mutes",
    "poll_votes",
    "polls",
    "preview_card_providers",
    "preview_card_trends",
    "preview_cards",
    "preview_cards_statuses",
    "quotes",
    "reports",
    "session_activations",
    "status_edits",
    "status_pins",
    "status_stats",
    "statuses",
    "statuses_tags",
    "tag_follows",
    "tags",
    "users",
]


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} REPLICA IDENTITY FULL;")


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} REPLICA IDENTITY DEFAULT;")
