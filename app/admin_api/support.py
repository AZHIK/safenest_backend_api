from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import require_operator_permission
from app.schemas.support import (
    SupportCenterResponse,
    SupportCenterCreate,
    SupportCenterUpdate,
    to_support_center_response
)
from app.services.support_service import support_service

router = APIRouter()


@router.get("", response_model=List[SupportCenterResponse])
async def list_support_centers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("support_centers.view"))
):
    """List all support centers for management."""
    centers = await support_service.get_all_centers(db, skip, limit)
    return [to_support_center_response(c) for c in centers]


@router.post("", response_model=SupportCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_support_center(
    data: SupportCenterCreate,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("support_centers.create"))
):
    """Create a new support center."""
    center = await support_service.create_center(db, data.model_dump())
    return to_support_center_response(center)


@router.get("/{center_id}", response_model=SupportCenterResponse)
async def get_support_center(
    center_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("support_centers.view"))
):
    """Get support center details."""
    try:
        center = await support_service.get_center_by_id(db, center_id)
        return to_support_center_response(center)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{center_id}", response_model=SupportCenterResponse)
async def update_support_center(
    center_id: UUID,
    data: SupportCenterUpdate,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("support_centers.update"))
):
    """Update a support center."""
    try:
        center = await support_service.update_center(db, center_id, data.model_dump(exclude_unset=True))
        return to_support_center_response(center)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{center_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_support_center(
    center_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("support_centers.delete"))
):
    """Delete a support center."""
    success = await support_service.delete_center(db, center_id)
    if not success:
        raise HTTPException(status_code=404, detail="Support center not found")
