from fastapi import APIRouter

from app.api.v1.endpoints import auth, sos, reports, messaging, support, training, health

api_router = APIRouter()

# Health check (no auth required)
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# SOS Emergency
api_router.include_router(sos.router, prefix="/sos", tags=["sos"])

# Incident Reporting
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

# Messaging
api_router.include_router(messaging.router, prefix="/messages", tags=["messages"])

# Support Centers
api_router.include_router(support.router, prefix="/support-centers", tags=["support"])

# Training
api_router.include_router(training.router, prefix="/training", tags=["training"])
