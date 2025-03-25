"""create feed_recommendations table

Revision ID: 6129ba708de9
Revises: 02c9f00fd297
Create Date: 2025-03-25 16:55:07.337226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6129ba708de9'
down_revision: Union[str, None] = '02c9f00fd297'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        'feed_recommendations',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('feed_id', sa.BigInteger, nullable=False),
        sa.Column('status_id', sa.BigInteger, nullable=False),
        sa.Column('source', sa.String, nullable=False),
        sa.Column('score', sa.Float, nullable=False),
        sa.Column('adjusted_score', sa.Float, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    op.create_foreign_key(
        'fk_feed_recommendations_feed_id', 
        'feed_recommendations', 
        'feeds', 
        ['feed_id'], 
        ['id'],
        ondelete='CASCADE'
    )

    op.create_foreign_key(
        'fk_feed_recommendations_status_id', 
        'feed_recommendations', 
        'statuses', 
        ['status_id'], 
        ['id'],
        ondelete='SET NULL'
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('feed_recommendations')
