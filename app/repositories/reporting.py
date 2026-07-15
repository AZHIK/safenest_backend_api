from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reporting import IncidentReport, EvidenceFile
from app.repositories.base import BaseRepository


class IncidentReportRepository(BaseRepository[IncidentReport]):
    def __init__(self):
        super().__init__(IncidentReport)

    async def get_by_report_number(
        self,
        db: AsyncSession,
        report_number: str
    ) -> Optional[IncidentReport]:
        result = await db.execute(
            select(IncidentReport).where(IncidentReport.report_number == report_number)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[IncidentReport]:
        result = await db.execute(
            select(IncidentReport)
            .where(IncidentReport.user_id == user_id)
            .order_by(IncidentReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def list_reports(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> List[IncidentReport]:
        result = await db.execute(
            select(IncidentReport)
            .order_by(IncidentReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_id_with_evidence(
        self,
        db: AsyncSession,
        report_id: UUID
    ) -> Optional[IncidentReport]:
        result = await db.execute(
            select(IncidentReport)
            .options(selectinload(IncidentReport.evidence_files))
            .where(IncidentReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def generate_report_number(self, db: AsyncSession) -> str:
        from datetime import datetime
        prefix = datetime.utcnow().strftime("%Y%m")

        # Get count of reports this month
        result = await db.execute(
            select(func.count(IncidentReport.id))
            .where(IncidentReport.report_number.like(f"{prefix}%"))
        )
        count = result.scalar() + 1

        return f"{prefix}-{count:06d}"


class EvidenceFileRepository(BaseRepository[EvidenceFile]):
    def __init__(self):
        super().__init__(EvidenceFile)

    async def get_by_original_filename(
        self,
        db: AsyncSession,
        original_filename: str
    ) -> Optional[EvidenceFile]:
        result = await db.execute(
            select(EvidenceFile)
            .where(EvidenceFile.original_filename == original_filename)
            .order_by(EvidenceFile.uploaded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_report(
        self,
        db: AsyncSession,
        report_id: UUID
    ) -> List[EvidenceFile]:
        result = await db.execute(
            select(EvidenceFile)
            .where(EvidenceFile.report_id == report_id)
            .order_by(EvidenceFile.uploaded_at)
        )
        return result.scalars().all()

    async def get_pending_processing(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> List[EvidenceFile]:
        result = await db.execute(
            select(EvidenceFile)
            .where(EvidenceFile.processing_status == "pending")
            .limit(limit)
        )
        return result.scalars().all()

    async def get_pending_virus_scan(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> List[EvidenceFile]:
        result = await db.execute(
            select(EvidenceFile)
            .where(EvidenceFile.virus_scan_status == "pending")
            .limit(limit)
        )
        return result.scalars().all()


incident_report_repo = IncidentReportRepository()
evidence_file_repo = EvidenceFileRepository()
