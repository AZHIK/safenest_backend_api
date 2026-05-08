"""
Operator Incident Reports API Routes

- GET /api/v1/operator/reports - List incident reports
"""

from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import require_operator_permission
from app.repositories.reporting import incident_report_repo
from app.schemas.reporting import IncidentReportResponse, to_incident_report_response

router = APIRouter()


@router.get(
    "",
    response_model=List[IncidentReportResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_operator_permission("reports.view"))],
)
async def list_reports(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List incident reports for operator review."""
    reports = await incident_report_repo.list_reports(db, skip=skip, limit=limit)
    return [to_incident_report_response(report) for report in reports]
