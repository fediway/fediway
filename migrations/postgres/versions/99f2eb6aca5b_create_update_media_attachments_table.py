"""create update_media_attachments table

Revision ID: 99f2eb6aca5b
Revises: 6129ba708de9
Create Date: 2025-03-25 16:55:43.664042

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "99f2eb6aca5b"
down_revision: Union[str, None] = "6129ba708de9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass
    # op.add_column('media_attachments', sa.Column('aspect_ratio', sa.Float))
    # op.add_column('media_attachments', sa.Column('duration_seconds', sa.Integer))
    # op.add_column('media_attachments', sa.Column('fps', sa.Integer))
    # op.add_column('media_attachments', sa.Column('preview_url', sa.String))
    # op.add_column('media_attachments', sa.Column('text_url', sa.String))


def downgrade() -> None:
    """Downgrade schema."""
    pass
    # op.drop_column('media_attachments', 'aspect_ratio')
    # op.drop_column('media_attachments', 'duration_seconds')
    # op.drop_column('media_attachments', 'fps')
    # op.drop_column('media_attachments', 'preview_url')
    # op.drop_column('media_attachments', 'text_url')
