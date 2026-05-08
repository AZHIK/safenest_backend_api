"""
Operator SOS Monitor API Routes

- GET /api/v1/operator/sos-monitor/alerts - List active alerts for monitor
- PATCH /api/v1/operator/sos-monitor/alerts/{alert_id}/status - Update alert status (assign, resolve, etc.)
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import require_operator_permission, get_current_operator
from app.models.user import User as Operator
from app.repositories.sos import sos_alert_repo
from app.schemas.sos import (
    SOSMonitorResponse,
    SOSStatusUpdate,
    to_sos_monitor_response
)

router = APIRouter()


@router.get(
    "/alerts",
    response_model=List[SOSMonitorResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_operator_permission("sos.view"))],
)
async def list_monitor_alerts(
    db: AsyncSession = Depends(get_db),
):
    """List active and recently resolved SOS alerts for the operator monitor."""
    alerts = await sos_alert_repo.get_monitor_alerts(db)
    return [to_sos_monitor_response(alert) for alert in alerts]


@router.patch(
    "/alerts/{alert_id}/status",
    response_model=SOSMonitorResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_operator_permission("sos.manage"))],
)
async def update_alert_status(
    alert_id: UUID,
    data: SOSStatusUpdate,
    current_operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update SOS alert status (assign, escalate, resolve)."""
    # Get the alert first to ensure it exists
    alert = await sos_alert_repo.get_by_id(db, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SOS alert not found"
        )

    # Use the responder ID from data if provided (e.g. assigning to someone else)
    # otherwise use the current operator's ID for assignment
    responder_id = data.assigned_responder_id or current_operator.id

    await sos_alert_repo.update_status(
        db,
        alert_id,
        data.status,
        data.resolution_notes,
        assigned_to=responder_id
    )

    # Re-fetch with relationships for response
    # Better: add a get_monitor_alert_by_id to repository, but for now we re-fetch all
    # and find the one we need to ensure consistency with the monitor view logic
    updated_alerts = await sos_alert_repo.get_monitor_alerts(db)
    for a in updated_alerts:
        if a.id == alert_id:
            return to_sos_monitor_response(a)
    
    # Fallback if not in the monitor list anymore (e.g. resolved long ago)
    refetched = await sos_alert_repo.get_monitor_alert_by_id(db, alert_id)
    return to_sos_monitor_response(refetched)
