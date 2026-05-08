from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sos import SOSAlert, LocationPing, SOSStatus
from app.models.user import User
from app.repositories.base import BaseRepository


class SOSAlertRepository(BaseRepository[SOSAlert]):
    def __init__(self):
        super().__init__(SOSAlert)

    async def get_active_by_user(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[SOSAlert]:
        result = await db.execute(
            select(SOSAlert)
            .where(
                SOSAlert.user_id == user_id,
                SOSAlert.status.in_([SOSStatus.ACTIVE, SOSStatus.ASSIGNED, SOSStatus.ESCALATED])
            )
            .order_by(SOSAlert.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_active_alerts(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> List[SOSAlert]:
        result = await db.execute(
            select(SOSAlert)
            .where(SOSAlert.status.in_([SOSStatus.ACTIVE, SOSStatus.ASSIGNED, SOSStatus.ESCALATED]))
            .order_by(SOSAlert.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_monitor_alerts(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> List[SOSAlert]:
        result = await db.execute(
            select(SOSAlert)
            .options(
                selectinload(SOSAlert.user).selectinload(User.trusted_contacts),
                selectinload(SOSAlert.location_pings)
            )
            .where(
                SOSAlert.status.in_([
                    SOSStatus.ACTIVE,
                    SOSStatus.ASSIGNED,
                    SOSStatus.ESCALATED
                ]) | (
                    (SOSAlert.status == SOSStatus.RESOLVED) &
                    (SOSAlert.created_at >= datetime.now(timezone.utc) - timedelta(hours=24))
                )
            )
            .order_by(SOSAlert.created_at.desc())
            .limit(limit)
        )
        alerts = result.scalars().all()
        for alert in alerts:
            if alert.location_pings:
                alert.location_pings = sorted(
                    alert.location_pings,
                    key=lambda x: x.recorded_at,
                    reverse=True
                )[:10]  # Only need recent ones for monitor
        return alerts

    async def get_by_id_with_locations(
        self,
        db: AsyncSession,
        alert_id: UUID,
        location_limit: int = 50
    ) -> Optional[SOSAlert]:
        result = await db.execute(
            select(SOSAlert)
            .options(
                selectinload(SOSAlert.location_pings.and_(LocationPing.id != None))
            )
            .where(SOSAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if alert and alert.location_pings:
            alert.location_pings = sorted(
                alert.location_pings,
                key=lambda x: x.recorded_at,
                reverse=True
            )[:location_limit]
        return alert

    async def get_monitor_alert_by_id(
        self,
        db: AsyncSession,
        alert_id: UUID,
        location_limit: int = 10
    ) -> Optional[SOSAlert]:
        result = await db.execute(
            select(SOSAlert)
            .options(
                selectinload(SOSAlert.user).selectinload(User.trusted_contacts),
                selectinload(SOSAlert.location_pings)
            )
            .where(SOSAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if alert and alert.location_pings:
            alert.location_pings = sorted(
                alert.location_pings,
                key=lambda x: x.recorded_at,
                reverse=True
            )[:location_limit]
        return alert

    async def get_recent_for_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 10
    ) -> List[SOSAlert]:
        result = await db.execute(
            select(SOSAlert)
            .where(SOSAlert.user_id == user_id)
            .order_by(SOSAlert.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_status(
        self,
        db: AsyncSession,
        alert_id: UUID,
        status: str,
        resolution_notes: Optional[str] = None,
        assigned_to: Optional[UUID] = None
    ) -> None:
        values = {"status": status}
        if status == SOSStatus.ASSIGNED and assigned_to:
            values["assigned_to"] = assigned_to
            values["assigned_at"] = datetime.now(timezone.utc)
        
        if status in [SOSStatus.RESOLVED, SOSStatus.CANCELLED]:
            values["resolved_at"] = datetime.now(timezone.utc)
            if assigned_to:
                values["resolved_by"] = assigned_to
        
        if resolution_notes:
            values["resolution_notes"] = resolution_notes

        await db.execute(
            update(SOSAlert)
            .where(SOSAlert.id == alert_id)
            .values(**values)
        )
        await db.flush()

    async def get_active_nearby(
        self,
        db: AsyncSession,
        lat: float,
        lng: float,
        radius_km: float = 5.0
    ) -> List[SOSAlert]:
        # Simple bounding box query - for production, use PostGIS
        lat_delta = radius_km / 111.0  # Approximate km per degree
        lng_delta = radius_km / (111.0 * abs(lat) or 1)

        result = await db.execute(
            select(SOSAlert)
            .where(
                SOSAlert.status == SOSStatus.ACTIVE,
                SOSAlert.initial_latitude.between(lat - lat_delta, lat + lat_delta),
                SOSAlert.initial_longitude.between(lng - lng_delta, lng + lng_delta)
            )
        )
        return result.scalars().all()


class LocationPingRepository(BaseRepository[LocationPing]):
    def __init__(self):
        super().__init__(LocationPing)

    async def get_by_alert(
        self,
        db: AsyncSession,
        alert_id: UUID,
        limit: int = 100
    ) -> List[LocationPing]:
        result = await db.execute(
            select(LocationPing)
            .where(LocationPing.alert_id == alert_id)
            .order_by(LocationPing.recorded_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_by_alert(
        self,
        db: AsyncSession,
        alert_id: UUID,
        minutes: int = 30
    ) -> List[LocationPing]:
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        result = await db.execute(
            select(LocationPing)
            .where(
                LocationPing.alert_id == alert_id,
                LocationPing.recorded_at >= since
            )
            .order_by(LocationPing.recorded_at.desc())
        )
        return result.scalars().all()

    async def create_batch(
        self,
        db: AsyncSession,
        pings_data: list[dict]
    ) -> List[LocationPing]:
        pings = [LocationPing(**data) for data in pings_data]
        db.add_all(pings)
        await db.flush()
        return pings


sos_alert_repo = SOSAlertRepository()
location_ping_repo = LocationPingRepository()
