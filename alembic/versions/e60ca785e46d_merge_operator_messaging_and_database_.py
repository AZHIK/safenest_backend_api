"""merge operator messaging and database changes

Revision ID: e60ca785e46d
Revises: 20260715, 38b8c77371c1
Create Date: 2026-07-15 16:08:57.132779

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e60ca785e46d'
down_revision = ('20260715', '38b8c77371c1')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
