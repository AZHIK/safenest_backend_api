"""
Admin RBAC API Router

Combines all operator management endpoints under /api/v1/operator prefix.
"""

from fastapi import APIRouter

from app.admin_api import auth, permissions, reports, roles, users, me, sos_monitor, training, support, dashboard, mobile_users, messaging

# Main router for /api/v1/operator prefix
operator_router = APIRouter()

# Dashboard stats: /api/v1/operator/dashboard/stats
operator_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["operator-dashboard"]
)

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

# SOS Monitor: /api/v1/operator/sos-monitor/*
operator_router.include_router(
    sos_monitor.router,
    prefix="/sos-monitor",
    tags=["operator-sos-monitor"]
)

# Permission registry: /api/v1/operator/permissions
operator_router.include_router(
    permissions.router,
    prefix="/permissions",
    tags=["operator-permissions"]
)

# Reports: /api/v1/operator/reports
operator_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["operator-reports"]
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

# Mobile application user management: /api/v1/operator/mobile-users
operator_router.include_router(
    mobile_users.router,
    prefix="/mobile-users",
    tags=["operator-mobile-users"]
)

# Training management: /api/v1/operator/training
operator_router.include_router(
    training.router,
    prefix="/training",
    tags=["operator-training"]
)

# Support centers management: /api/v1/operator/support-centers
operator_router.include_router(
    support.router,
    prefix="/support-centers",
    tags=["operator-support-centers"]
)

# Messaging management: /api/v1/operator/messaging
operator_router.include_router(
    messaging.router,
    prefix="/messaging",
    tags=["operator-messaging"]
)
