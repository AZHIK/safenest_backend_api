from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support import SupportCenter
from app.repositories.support import support_center_repo


class SupportService:
    async def find_nearby_centers(
        self,
        db: AsyncSession,
        request
    ) -> List[SupportCenter]:
        """Find nearby support centers. Returns ORM objects (caller must map to schema)."""
        return await support_center_repo.get_nearby(
            db,
            request.latitude,
            request.longitude,
            request.radius_km,
            center_types=request.center_types or None,
            is_24_7=request.is_24_7,
            provides_medical=request.provides_medical,
            provides_legal=request.provides_legal,
            provides_shelter=request.provides_shelter,
            limit=50
        )

    async def get_center_by_id(
        self,
        db: AsyncSession,
        center_id: UUID
    ) -> SupportCenter:
        """Get center by ID. Returns ORM object (caller must map to schema)."""
        center = await support_center_repo.get_by_id(db, center_id)
        if not center:
            raise ValueError("Support center not found")
        return center

    async def get_centers_by_type(
        self,
        db: AsyncSession,
        center_type: str,
        city: str = None
    ) -> List[SupportCenter]:
        """Get centers by type. Returns ORM objects (caller must map to schema)."""
        return await support_center_repo.get_by_type(db, center_type, city)

    async def get_verified_centers(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> List[SupportCenter]:
        """Get verified centers. Returns ORM objects (caller must map to schema)."""
        return await support_center_repo.get_verified(db, limit)

    # --- Management Methods ---

    async def get_all_centers(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[SupportCenter]:
        """Get all centers for admin management."""
        return await support_center_repo.get_all(db, skip, limit)

    async def create_center(
        self,
        db: AsyncSession,
        data: dict
    ) -> SupportCenter:
        # If geo_location is needed, it would be handled here or in repo
        return await support_center_repo.create(db, data)

    async def update_center(
        self,
        db: AsyncSession,
        center_id: UUID,
        data: dict
    ) -> SupportCenter:
        center = await support_center_repo.get_by_id(db, center_id)
        if not center:
            raise ValueError("Support center not found")
        return await support_center_repo.update(db, center, data)

    async def delete_center(
        self,
        db: AsyncSession,
        center_id: UUID
    ) -> bool:
        return await support_center_repo.delete(db, center_id)


support_service = SupportService()
