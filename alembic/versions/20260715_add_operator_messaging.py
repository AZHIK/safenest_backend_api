"""
Add Operator support to messaging

Revision ID: 20260715
Revises: 20260503
Create Date: 2026-07-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers
revision: str = '20260715'
down_revision: Union[str, None] = '20260503'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add operator_user_id to conversation_participants
    op.add_column('conversation_participants', sa.Column('operator_user_id', sqlmodel.sql.sqltypes.GUID(), nullable=True))
    op.create_index('ix_conversation_participants_operator_user_id', 'conversation_participants', ['operator_user_id'])
    op.create_foreign_key('fk_conversation_participants_operator_user_id_operator_users', 'conversation_participants', 'operator_users', ['operator_user_id'], ['id'], ondelete='CASCADE')

    # Make user_id nullable
    op.alter_column('conversation_participants', 'user_id', existing_type=sqlmodel.sql.sqltypes.GUID(), nullable=True)

    # Add sender_operator_id to messages
    op.add_column('messages', sa.Column('sender_operator_id', sqlmodel.sql.sqltypes.GUID(), nullable=True))
    op.create_index('ix_messages_sender_operator_id', 'messages', ['sender_operator_id'])
    op.create_foreign_key('fk_messages_sender_operator_id_operator_users', 'messages', 'operator_users', ['sender_operator_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_messages_sender_operator_id_operator_users', 'messages', type_='foreignkey')
    op.drop_index('ix_messages_sender_operator_id', table_name='messages')
    op.drop_column('messages', 'sender_operator_id')

    op.alter_column('conversation_participants', 'user_id', existing_type=sqlmodel.sql.sqltypes.GUID(), nullable=False)

    op.drop_constraint('fk_conversation_participants_operator_user_id_operator_users', 'conversation_participants', type_='foreignkey')
    op.drop_index('ix_conversation_participants_operator_user_id', table_name='conversation_participants')
    op.drop_column('conversation_participants', 'operator_user_id')
