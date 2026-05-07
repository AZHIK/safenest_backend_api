"""
SQLModel definitions for Operator RBAC system

Models:
- OperatorUser: Institutional operator users
- Role: Role definitions
- RolePermissionLink: Many-to-many role-permission assignments
- UserRoleLink: Many-to-many user-role assignments
- UserPermissionOverride: Direct user permission overrides (grant/deny)
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Column, DateTime, String, Text, Boolean, ForeignKey, Table, func
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field


# Link table: User <-> Role (many-to-many)
class UserRoleLink(SQLModel, table=True):
    """Many-to-many link between operators and roles."""
    __tablename__ = "operator_user_role_links"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="operator_users.id", index=True)
    role_id: uuid.UUID = Field(foreign_key="operator_roles.id", index=True)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


# Link table: Role <-> Permission (many-to-many)
class RolePermissionLink(SQLModel, table=True):
    """Many-to-many link between roles and permissions.
    
    permission_code stores values from PermissionEnum (string values).
    """
    __tablename__ = "operator_role_permission_links"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    role_id: uuid.UUID = Field(foreign_key="operator_roles.id", index=True)
    permission_code: str = Field(max_length=100, index=True)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class Role(SQLModel, table=True):
    """
    Operator Role definition.
    
    System roles have is_system=True and cannot be deleted.
    """
    __tablename__ = "operator_roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_system: bool = Field(default=False, index=True)
    
    # Timestamps
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, is_system={self.is_system})>"


class OperatorUser(SQLModel, table=True):
    """
    Institutional Operator User
    
    Separate from mobile app users (survivors).
    Used for police, legal officers, counselors, help center staff, etc.
    """
    __tablename__ = "operator_users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Basic info
    full_name: str = Field(max_length=200)
    email: str = Field(max_length=255, unique=True, index=True)
    phone: Optional[str] = Field(default=None, max_length=30, index=True)
    
    # Security
    password_hash: str = Field(max_length=255)
    
    # Status flags
    is_active: bool = Field(default=True, index=True)
    is_super_admin: bool = Field(default=False, index=True)
    
    # Failed login tracking
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    last_login: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    
    # Email verification
    email_verified: bool = Field(default=False)
    email_verified_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    
    # Password reset
    password_reset_token: Optional[str] = Field(default=None, max_length=255)
    password_reset_expires: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    
    # JWT tracking
    current_jti: Optional[str] = Field(default=None, max_length=255)
    
    # Timestamps
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    def __repr__(self) -> str:
        return f"<OperatorUser(id={self.id}, email={self.email}, is_active={self.is_active})>"

    @property
    def is_locked(self) -> bool:
        """Check if account is temporarily locked."""
        if self.locked_until and self.locked_until > datetime.now(timezone.utc):
            return True
        return False


class UserPermissionOverride(SQLModel, table=True):
    """
    Direct permission override for an operator user.
    
    Allows granting or denying specific permissions directly to a user,
    regardless of their role permissions.
    
    granted=True: Explicitly grant this permission
    granted=False: Explicitly deny this permission (overrides role grants)
    """
    __tablename__ = "operator_user_permission_overrides"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="operator_users.id", index=True)
    permission_code: str = Field(max_length=100, index=True)
    granted: bool = Field(default=True, index=True)  # True=grant, False=deny
    
    # Reason for override (audit trail)
    reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Who created this override
    created_by: Optional[uuid.UUID] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    def __repr__(self) -> str:
        action = "GRANT" if self.granted else "DENY"
        return f"<UserPermissionOverride(user_id={self.user_id}, perm={self.permission_code}, {action})>"


# Add back-populates to Role links
Role.permission_links = relationship(
    "RolePermissionLink",
    back_populates="role",
    lazy="selectin",
    cascade="all, delete-orphan"
)

Role.user_links = relationship(
    "UserRoleLink",
    back_populates="role",
    lazy="selectin",
    cascade="all, delete-orphan"
)

UserRoleLink.role = relationship("Role", back_populates="user_links", lazy="selectin")
UserRoleLink.user = relationship("OperatorUser", back_populates="role_links")

RolePermissionLink.role = relationship("Role", back_populates="permission_links")

# Add relationships to OperatorUser
OperatorUser.role_links = relationship(
    "UserRoleLink",
    back_populates="user",
    lazy="selectin",
    cascade="all, delete-orphan"
)

OperatorUser.permission_overrides = relationship(
    "UserPermissionOverride",
    back_populates="user",
    lazy="selectin",
    cascade="all, delete-orphan"
)

# Add relationship to UserPermissionOverride
UserPermissionOverride.user = relationship("OperatorUser", back_populates="permission_overrides")
