"""
Add Operator RBAC models

Revision ID: 20260503
Revises: a2f8490ce0cd
Create Date: 2026-05-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers
revision: str = '20260503'
down_revision: Union[str, None] = 'a2f8490ce0cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create operator_roles table
    op.create_table(
        'operator_roles',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_operator_roles_is_system', 'operator_roles', ['is_system'])
    op.create_index('ix_operator_roles_name', 'operator_roles', ['name'])

    # Create operator_users table
    op.create_table(
        'operator_users',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_super_admin', sa.Boolean(), nullable=False),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_reset_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_jti', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_operator_users_email', 'operator_users', ['email'])
    op.create_index('ix_operator_users_is_active', 'operator_users', ['is_active'])
    op.create_index('ix_operator_users_is_super_admin', 'operator_users', ['is_super_admin'])
    op.create_index('ix_operator_users_phone', 'operator_users', ['phone'])

    # Create operator_user_role_links table
    op.create_table(
        'operator_user_role_links',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('role_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['operator_roles.id']),
        sa.ForeignKeyConstraint(['user_id'], ['operator_users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_operator_user_role_links_role_id', 'operator_user_role_links', ['role_id'])
    op.create_index('ix_operator_user_role_links_user_id', 'operator_user_role_links', ['user_id'])

    # Create operator_role_permission_links table
    op.create_table(
        'operator_role_permission_links',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('role_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('permission_code', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['operator_roles.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_operator_role_permission_links_permission_code', 'operator_role_permission_links', ['permission_code'])
    op.create_index('ix_operator_role_permission_links_role_id', 'operator_role_permission_links', ['role_id'])

    # Create operator_user_permission_overrides table
    op.create_table(
        'operator_user_permission_overrides',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('permission_code', sa.String(length=100), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_by', sqlmodel.sql.sqltypes.GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['operator_users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_operator_user_permission_overrides_granted', 'operator_user_permission_overrides', ['granted'])
    op.create_index('ix_operator_user_permission_overrides_permission_code', 'operator_user_permission_overrides', ['permission_code'])
    op.create_index('ix_operator_user_permission_overrides_user_id', 'operator_user_permission_overrides', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_operator_user_permission_overrides_user_id', table_name='operator_user_permission_overrides')
    op.drop_index('ix_operator_user_permission_overrides_permission_code', table_name='operator_user_permission_overrides')
    op.drop_index('ix_operator_user_permission_overrides_granted', table_name='operator_user_permission_overrides')
    op.drop_table('operator_user_permission_overrides')
    
    op.drop_index('ix_operator_role_permission_links_role_id', table_name='operator_role_permission_links')
    op.drop_index('ix_operator_role_permission_links_permission_code', table_name='operator_role_permission_links')
    op.drop_table('operator_role_permission_links')
    
    op.drop_index('ix_operator_user_role_links_user_id', table_name='operator_user_role_links')
    op.drop_index('ix_operator_user_role_links_role_id', table_name='operator_user_role_links')
    op.drop_table('operator_user_role_links')
    
    op.drop_index('ix_operator_users_phone', table_name='operator_users')
    op.drop_index('ix_operator_users_is_super_admin', table_name='operator_users')
    op.drop_index('ix_operator_users_is_active', table_name='operator_users')
    op.drop_index('ix_operator_users_email', table_name='operator_users')
    op.drop_table('operator_users')
    
    op.drop_index('ix_operator_roles_name', table_name='operator_roles')
    op.drop_index('ix_operator_roles_is_system', table_name='operator_roles')
    op.drop_table('operator_roles')
