from fastapi import APIRouter

from app.api.v1.endpoints import auth, sos, reports, messaging, support, training, health, evidence
from app.admin_api.router import operator_router

api_router = APIRouter()

# Health check (no auth required)
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# SOS Emergency
api_router.include_router(sos.router, prefix="/sos", tags=["sos"])

# Incident Reporting
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(reports.router, prefix="/incident-reports", tags=["incident-reports"])

# Evidence Files
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])

# Messaging
api_router.include_router(messaging.router, prefix="/messages", tags=["messages"])

# Support Centers
api_router.include_router(support.router, prefix="/support-centers", tags=["support"])

# Training
api_router.include_router(training.router, prefix="/training", tags=["training"])

# Operator RBAC Management (separate from survivor auth)
api_router.include_router(operator_router, prefix="/operator", tags=["operator-rbac"])
