from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin, ST_Point

from app.models.support import SupportCenter
from app.repositories.base import BaseRepository


class SupportCenterRepository(BaseRepository[SupportCenter]):
    def __init__(self):
        super().__init__(SupportCenter)

    async def get_nearby(
        self,
        db: AsyncSession,
        lat: float,
        lng: float,
        radius_km: float = 10.0,
        center_types: Optional[List[str]] = None,
        is_24_7: Optional[bool] = None,
        provides_medical: Optional[bool] = None,
        provides_legal: Optional[bool] = None,
        provides_shelter: Optional[bool] = None,
        limit: int = 50
    ) -> List[SupportCenter]:
        # Use simple bounding box for now - production should use PostGIS
        import math
        lat_delta = radius_km / 111.0
        lat_rad = math.radians(lat)
        cos_lat = max(math.cos(lat_rad), 0.01)
        lng_delta = radius_km / (111.0 * cos_lat)

        query = select(SupportCenter).where(
            SupportCenter.is_active == True,
            SupportCenter.temporarily_closed == False,
            SupportCenter.latitude.between(lat - lat_delta, lat + lat_delta),
            SupportCenter.longitude.between(lng - lng_delta, lng + lng_delta)
        )

        if center_types:
            query = query.where(SupportCenter.center_type.in_(center_types))
        if is_24_7 is not None:
            query = query.where(SupportCenter.is_24_7 == is_24_7)
        if provides_medical is not None:
            query = query.where(SupportCenter.provides_medical == provides_medical)
        if provides_legal is not None:
            query = query.where(SupportCenter.provides_legal == provides_legal)
        if provides_shelter is not None:
            query = query.where(SupportCenter.provides_shelter == provides_shelter)

        result = await db.execute(query.limit(limit))
        centers = result.scalars().all()

        # Calculate and attach distance
        for center in centers:
            object.__setattr__(center, 'distance_km', self._haversine_distance(lat, lng, center.latitude, center.longitude))

        # Sort by distance
        return sorted(centers, key=lambda c: c.distance_km)[:limit]

    async def get_by_type(
        self,
        db: AsyncSession,
        center_type: str,
        city: Optional[str] = None,
        limit: int = 50
    ) -> List[SupportCenter]:
        query = select(SupportCenter).where(
            SupportCenter.center_type == center_type,
            SupportCenter.is_active == True
        )
        if city:
            query = query.where(func.lower(SupportCenter.city) == city.lower())

        result = await db.execute(query.limit(limit))
        return result.scalars().all()

    async def get_verified(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> List[SupportCenter]:
        result = await db.execute(
            select(SupportCenter)
            .where(
                SupportCenter.is_verified == True,
                SupportCenter.is_active == True
            )
            .order_by(SupportCenter.rating_average.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate the great circle distance between two points in km."""
        import math

        R = 6371  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


support_center_repo = SupportCenterRepository()
