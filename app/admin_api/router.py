"""
Admin RBAC API Router

Combines all operator management endpoints under /api/v1/operator prefix.
"""

from fastapi import APIRouter

from app.admin_api import auth, permissions, roles, users, me

# Main router for /api/v1/operator prefix
operator_router = APIRouter()

# Authentication routes: /api/v1/operator/auth/*
operator_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["operator-auth"]
)

# Current user routes: /api/v1/operator/me/*
operator_router.include_router(
    me.router,
    prefix="/me",
    tags=["operator-me"]
)

# Permission registry: /api/v1/operator/permissions
operator_router.include_router(
    permissions.router,
    prefix="/permissions",
    tags=["operator-permissions"]
)

# Role management: /api/v1/operator/roles
operator_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["operator-roles"]
)

# User management: /api/v1/operator/users
operator_router.include_router(
    users.router,
    prefix="/users",
    tags=["operator-users"]
)
