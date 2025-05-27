"""create publiction

Revision ID: f121f86f8f36
Revises: a4e04f9f295e
Create Date: 2025-04-19 14:01:53.217177

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f121f86f8f36"
down_revision: Union[str, None] = "a4e04f9f295e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
    CREATE PUBLICATION risingwave_pub
        FOR TABLE public.accounts,
                  public.account_stats,
                  public.statuses,
                  public.status_stats,
                  public.follows,
                  public.follow_requests,
                  public.mentions,
                  public.favourites,
                  public.tags,
                  public.tag_follows,
                  public.statuses_tags,
                  public.media_attachments,
                  public.users,
                  public.polls,
                  public.poll_votes,
                  public.mutes;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
    DROP PUBLICATION risingwave_pub;
    """)
