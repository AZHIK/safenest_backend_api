from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import security_logger
from app.db.redis import sos_cache
from app.models.sos import SOSAlert, LocationPing, SOSStatus
from app.repositories.sos import sos_alert_repo, location_ping_repo
from app.repositories.user import trusted_contact_repo
from app.schemas.sos import (
    SOSCreate,
    SOSStatusUpdate,
    LocationPingCreate,
)
from app.workers.tasks import notify_contacts_async, notify_support_centers_async

settings = get_settings()


class SOSService:
    async def trigger_sos(
        self,
        db: AsyncSession,
        user_id: UUID,
        data: SOSCreate
    ) -> SOSAlert:
        """Trigger SOS and return SOSAlert ORM (with location_pings eager-loaded)."""
        # Check for existing active alert
        existing = await sos_alert_repo.get_active_by_user(db, user_id)
        if existing:
            # Return existing alert with updated location
            return await self._update_existing_alert(db, existing, data)

        # Create new alert
        alert_data = {
            "user_id": user_id,
            "status": SOSStatus.ACTIVE,
            "alert_type": data.alert_type,
            "severity": "high",
            "initial_latitude": data.latitude,
            "initial_longitude": data.longitude,
            "initial_accuracy": data.accuracy,
            "message": data.message,
            "triggered_by_device_id": data.triggered_by_device_id,
            "battery_level": data.battery_level,
            "client_created_at": data.client_created_at,
            "offline_id": data.offline_id,
        }

        alert = await sos_alert_repo.create(db, alert_data)

        # Cache in Redis for fast access
        await sos_cache.cache_alert(
            str(alert.id),
            {
                "user_id": str(user_id),
                "status": SOSStatus.ACTIVE,
                "lat": data.latitude,
                "lng": data.longitude,
                "started_at": alert.created_at.isoformat()
            }
        )

        # Log the emergency
        security_logger.log_sos_triggered(
            str(user_id),
            str(alert.id),
            data.latitude,
            data.longitude
        )

        # Queue notifications (async)
        await self._queue_notifications(db, user_id, alert, data)

        return alert

    async def update_location(
        self,
        db: AsyncSession,
        alert_id: UUID,
        data: LocationPingCreate
    ) -> LocationPing:
        """Update location and return LocationPing ORM."""
        # Verify the SOS alert exists
        alert = await sos_alert_repo.get_by_id(db, alert_id)
        if not alert:
            raise ValueError("SOS alert not found")

        ping_data = {
            "alert_id": alert_id,
            "user_id": alert.user_id,
            "latitude": data.latitude,
            "longitude": data.longitude,
            "accuracy": data.accuracy,
            "altitude": data.altitude,
            "speed": data.speed,
            "heading": data.heading,
            "battery_level": data.battery_level,
            "network_type": data.network_type,
            "signal_strength": data.signal_strength,
            "recorded_at": data.recorded_at,
            "offline_sequence": data.offline_sequence,
        }

        ping = await location_ping_repo.create(db, ping_data)

        # Update cache
        await sos_cache.update_location(
            str(alert_id),
            data.latitude,
            data.longitude,
            data.recorded_at.isoformat()
        )

        return ping

    async def update_sos_status(
        self,
        db: AsyncSession,
        alert_id: UUID,
        user_id: UUID,
        data: SOSStatusUpdate
    ) -> SOSAlert:
        """Update SOS status and return SOSAlert ORM."""
        # Verify user owns this alert
        alert = await sos_alert_repo.get_by_id(db, alert_id)
        if not alert or str(alert.user_id) != str(user_id):
            raise ValueError("Alert not found or access denied")

        await sos_alert_repo.update_status(
            db,
            alert_id,
            data.status,
            data.resolution_notes
        )

        # Update cache
        await sos_cache.cache_alert(
            str(alert_id),
            {
                "user_id": str(user_id),
                "status": data.status,
                "resolved_at": datetime.now(timezone.utc).isoformat()
            },
            expire_seconds=3600
        )

        # Refresh and return
        updated = await sos_alert_repo.get_by_id(db, alert_id)
        return updated

    async def get_sos_status(
        self,
        db: AsyncSession,
        alert_id: UUID,
        user_id: UUID
    ) -> SOSAlert:
        """Get SOS status and return SOSAlert ORM (with location_pings eager-loaded)."""
        # Get from database with recent locations
        alert = await sos_alert_repo.get_by_id_with_locations(db, alert_id, location_limit=20)

        if not alert or str(alert.user_id) != str(user_id):
            raise ValueError("Alert not found or access denied")

        return alert

    async def get_active_for_user(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[SOSAlert]:
        """Get active SOS for user and return SOSAlert ORM."""
        return await sos_alert_repo.get_active_by_user(db, user_id)

    async def get_history_for_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20
    ) -> List[SOSAlert]:
        """Get SOS history for user and return list of SOSAlert ORMs."""
        return await sos_alert_repo.get_recent_for_user(db, user_id, limit)

    async def process_offline_locations(
        self,
        db: AsyncSession,
        alert_id: UUID,
        locations: List[LocationPingCreate]
    ) -> List[LocationPing]:
        """Process offline locations and return list of LocationPing ORMs."""
        pings_data = [
            {
                "alert_id": alert_id,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "accuracy": loc.accuracy,
                "altitude": loc.altitude,
                "speed": loc.speed,
                "heading": loc.heading,
                "battery_level": loc.battery_level,
                "network_type": loc.network_type,
                "recorded_at": loc.recorded_at,
                "offline_sequence": loc.offline_sequence,
            }
            for loc in locations
        ]

        return await location_ping_repo.create_batch(db, pings_data)

    async def _update_existing_alert(
        self,
        db: AsyncSession,
        alert: SOSAlert,
        data: SOSCreate
    ) -> SOSAlert:
        """Update existing alert with new location and return SOSAlert ORM."""
        # Just update location via the location ping service
        ping_data = LocationPingCreate(
            alert_id=alert.id,
            latitude=data.latitude,
            longitude=data.longitude,
            accuracy=data.accuracy,
            altitude=data.altitude,
            speed=data.speed,
            heading=data.heading,
            battery_level=data.battery_level,
            network_type=data.network_type,
            recorded_at=data.client_created_at or datetime.now(timezone.utc)
        )
        await self.update_location(db, alert.id, ping_data)

        return alert

    async def _queue_notifications(
        self,
        db: AsyncSession,
        user_id: UUID,
        alert: SOSAlert,
        data: SOSCreate
    ):
        # Get trusted contacts
        contacts = await trusted_contact_repo.get_by_user(db, user_id)

        # Queue notification tasks
        if contacts:
            notify_contacts_async.delay(
                str(user_id),
                str(alert.id),
                [str(c.id) for c in contacts],
                {
                    "lat": data.latitude,
                    "lng": data.longitude,
                    "message": data.message
                }
            )

        # Queue nearby support center notifications
        notify_support_centers_async.delay(
            str(alert.id),
            data.latitude,
            data.longitude
        )


sos_service = SOSService()
