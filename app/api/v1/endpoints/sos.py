from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_verified
from app.models.user import User
from app.schemas.sos import (
    SOSCreate,
    SOSResponse,
    SOSStatusUpdate,
    LocationPingCreate,
    LocationPingResponse,
    SOSWithLocationsResponse,
    to_sos_response,
    to_sos_with_locations_response,
    to_location_ping_response,
)
from app.schemas.common import SuccessResponse
from app.services.sos_service import sos_service

router = APIRouter()


@router.post("/trigger", response_model=SOSResponse, status_code=status.HTTP_201_CREATED)
async def trigger_sos(
    data: SOSCreate,
    current_user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    """Trigger an SOS emergency alert."""
    alert = await sos_service.trigger_sos(db, current_user.id, data)
    return to_sos_response(alert)


@router.post("/location-update", response_model=LocationPingResponse)
async def update_location(
    data: LocationPingCreate,
    current_user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    """Update location for an active SOS alert."""
    try:
        ping = await sos_service.update_location(db, data.alert_id, data)
        return to_location_ping_response(ping)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/location-batch")
async def batch_update_locations(
    alert_id: UUID,
    locations: List[LocationPingCreate],
    current_user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db)
):
    """Batch update locations (for offline sync)."""
    try:
        pings = await sos_service.process_offline_locations(db, alert_id, locations)
        return {
            "message": f"Processed {len(pings)} locations",
            "locations": [to_location_ping_response(p) for p in pings]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/status/{alert_id}", response_model=SOSWithLocationsResponse)
async def get_sos_status(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get status and location history of an SOS alert."""
    try:
        alert = await sos_service.get_sos_status(db, alert_id, current_user.id)
        return to_sos_with_locations_response(alert)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/active", response_model=Optional[SOSResponse])
async def get_active_sos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active SOS alert for current user, if any."""
    alert = await sos_service.get_active_for_user(db, current_user.id)
    if alert:
        return to_sos_response(alert)
    return None


@router.patch("/{alert_id}/status", response_model=SOSResponse)
async def update_sos_status(
    alert_id: UUID,
    data: SOSStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update SOS alert status (resolve or cancel)."""
    try:
        alert = await sos_service.update_sos_status(
            db,
            alert_id,
            current_user.id,
            data
        )
        return to_sos_response(alert)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/history", response_model=List[SOSResponse])
async def get_sos_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get SOS alert history for current user."""
    alerts = await sos_service.get_history_for_user(db, current_user.id, limit)
    return [to_sos_response(a) for a in alerts]
