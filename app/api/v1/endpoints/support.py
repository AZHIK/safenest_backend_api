from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, allow_anonymous
from app.schemas.support import SupportCenterNearbyRequest, SupportCenterResponse, to_support_center_response
from app.services.support_service import support_service

router = APIRouter()


@router.post("/nearby", response_model=List[SupportCenterResponse])
async def find_nearby_centers(
    request: SupportCenterNearbyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Find support centers near a location."""
    centers = await support_service.find_nearby_centers(db, request)
    return [to_support_center_response(c) for c in centers]


@router.get("/{center_id}", response_model=SupportCenterResponse)
async def get_center(
    center_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get support center details."""
    try:
        center = await support_service.get_center_by_id(db, center_id)
        return to_support_center_response(center)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/type/{center_type}", response_model=List[SupportCenterResponse])
async def get_centers_by_type(
    center_type: str,
    city: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get support centers by type."""
    centers = await support_service.get_centers_by_type(db, center_type, city)
    return [to_support_center_response(c) for c in centers]


@router.get("/verified/list", response_model=List[SupportCenterResponse])
async def get_verified_centers(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get verified support centers."""
    centers = await support_service.get_verified_centers(db, limit)
    return [to_support_center_response(c) for c in centers]
