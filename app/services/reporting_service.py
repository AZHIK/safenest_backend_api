import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import security_logger
from app.repositories.reporting import incident_report_repo, evidence_file_repo
from app.repositories.user import user_repo
from app.schemas.reporting import (
    IncidentReportCreate,
    EvidenceUpload,
)
from app.models.reporting import IncidentReport, EvidenceFile
from app.services.storage_service import storage_service

settings = get_settings()


class ReportingService:
    async def create_report(
        self,
        db: AsyncSession,
        user_id: UUID,
        data: IncidentReportCreate
    ) -> IncidentReport:
        """Create report and return IncidentReport ORM."""
        # Generate report number
        report_number = await incident_report_repo.generate_report_number(db)

        report_data = {
            "user_id": user_id,
            "report_number": report_number,
            "report_type": data.report_type,
            "status": "submitted",
            "incident_date": data.incident_date,
            "incident_latitude": data.incident_latitude,
            "incident_longitude": data.incident_longitude,
            "incident_address": data.incident_address,
            "is_anonymous": data.is_anonymous,
            "reporter_age_range": data.reporter_age_range,
            "reporter_gender": data.reporter_gender,
            "description_encrypted": data.description_encrypted,
            "encryption_metadata": data.encryption_metadata,
            "follow_up_preference": data.follow_up_preference,
            "contact_email_encrypted": data.contact_email_encrypted,
            "contact_phone_encrypted": data.contact_phone_encrypted,
            "client_created_at": data.client_created_at,
            "offline_id": data.offline_id,
        }

        report = await incident_report_repo.create(db, report_data)

        security_logger.log_file_upload(
            str(user_id),
            "report",
            True,
            len(data.description_encrypted) if data.description_encrypted else 0
        )

        return report

    async def get_report(
        self,
        db: AsyncSession,
        report_id: UUID,
        user_id: UUID
    ) -> IncidentReport:
        """Get report with evidence and return IncidentReport ORM (with evidence_files eager-loaded)."""
        report = await incident_report_repo.get_by_id_with_evidence(db, report_id)

        if not report:
            raise ValueError("Report not found")

        # Verify access
        if str(report.user_id) != str(user_id):
            raise ValueError("Access denied")

        return report

    async def get_user_reports(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[IncidentReport]:
        """Get user reports and return list of IncidentReport ORMs."""
        return await incident_report_repo.get_by_user(db, user_id, skip, limit)

    async def process_evidence_upload(
        self,
        db: AsyncSession,
        user_id: UUID,
        data: EvidenceUpload,
        file_content: bytes
    ) -> EvidenceFile:
        """Process evidence upload and return EvidenceFile ORM."""
        # Verify report exists and belongs to user
        report = await incident_report_repo.get_by_id(db, data.report_id)
        if not report or str(report.user_id) != str(user_id):
            raise ValueError("Report not found or access denied")

        # Validate file size
        if len(file_content) > settings.max_file_size_bytes:
            raise ValueError(f"File exceeds maximum size of {settings.max_file_size_mb}MB")

        # Store file
        file_hash = hashlib.sha256(file_content).hexdigest()
        storage_path = await storage_service.store_evidence(
            file_content,
            data.file_type,
            file_hash,
            data.encryption_metadata.get("content_type", "application/octet-stream")
        )

        evidence_data = {
            "report_id": data.report_id,
            "uploaded_by": user_id,
            "file_type": data.file_type,
            "original_filename": data.original_filename,
            "mime_type": data.mime_type,
            "file_size_bytes": len(file_content),
            "storage_provider": storage_service.provider,
            "storage_path": storage_path,
            "storage_bucket": storage_service.bucket_name,
            "file_encryption_key_encrypted": data.encryption_metadata.get("encrypted_key"),
            "encryption_iv": data.encryption_metadata.get("iv"),
            "encryption_metadata": data.encryption_metadata,
            "file_hash_sha256": file_hash,
            "has_gps_metadata": data.has_gps_metadata,
            "gps_latitude": data.gps_latitude,
            "gps_longitude": data.gps_longitude,
            "recorded_at": data.recorded_at,
            "offline_id": data.offline_id,
        }

        evidence = await evidence_file_repo.create(db, evidence_data)

        security_logger.log_file_upload(
            str(user_id),
            data.file_type,
            True,
            len(file_content)
        )

        return evidence

    async def get_evidence_download_url(
        self,
        db: AsyncSession,
        evidence_id: UUID,
        user_id: UUID
    ) -> str:
        evidence = await evidence_file_repo.get_by_id(db, evidence_id)

        if not evidence:
            raise ValueError("Evidence not found")

        # Verify report ownership
        report = await incident_report_repo.get_by_id(db, evidence.report_id)
        if not report or str(report.user_id) != str(user_id):
            raise ValueError("Access denied")

        return await storage_service.get_presigned_url(
            evidence.storage_path,
            expires_seconds=3600
        )


reporting_service = ReportingService()
