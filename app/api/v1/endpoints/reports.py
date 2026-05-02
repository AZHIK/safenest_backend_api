from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, allow_anonymous
from app.core.config import get_settings
from app.models.user import User
from app.schemas.reporting import (
    IncidentReportCreate,
    IncidentReportResponse,
    ReportWithEvidenceResponse,
    EvidenceUpload,
    EvidenceFileResponse,
    to_incident_report_response,
    to_report_with_evidence_response,
    to_evidence_file_response,
)
from app.schemas.common import SuccessResponse
from app.services.reporting_service import reporting_service

settings = get_settings()
router = APIRouter()


@router.post("/create", response_model=IncidentReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: IncidentReportCreate,
    current_user: User = Depends(allow_anonymous),
    db: AsyncSession = Depends(get_db)
):
    """Create a new incident report."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        report = await reporting_service.create_report(db, current_user.id, data)
        return to_incident_report_response(report)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my-reports", response_model=List[IncidentReportResponse])
async def get_my_reports(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's incident reports."""
    reports = await reporting_service.get_user_reports(
        db,
        current_user.id,
        skip,
        limit
    )
    return [to_incident_report_response(r) for r in reports]


@router.get("/{report_id}", response_model=ReportWithEvidenceResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific report with evidence."""
    try:
        report = await reporting_service.get_report(db, report_id, current_user.id)
        return to_report_with_evidence_response(report)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/upload-evidence", response_model=EvidenceFileResponse)
async def upload_evidence(
    report_id: UUID = Form(...),
    file_type: str = Form(..., pattern=r"^(image|audio|video|document)$"),
    encryption_metadata: str = Form(...),
    file_hash_sha256: str = Form(...),
    has_gps_metadata: bool = Form(False),
    gps_latitude: float = Form(None),
    gps_longitude: float = Form(None),
    recorded_at: str = Form(None),
    offline_id: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload encrypted evidence file for a report."""
    # Validate file type
    if file_type == "image" and file.content_type not in settings.allowed_image_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type: {file.content_type}"
        )
    if file_type == "audio" and file.content_type not in settings.allowed_audio_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audio type: {file.content_type}"
        )

    # Read file content
    file_content = await file.read()

    if len(file_content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_file_size_mb}MB"
        )

    # Parse encryption metadata
    import json
    try:
        enc_meta = json.loads(encryption_metadata)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid encryption_metadata JSON"
        )

    # Parse recorded_at if provided
    rec_at = None
    if recorded_at:
        from datetime import datetime
        try:
            rec_at = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
        except ValueError:
            pass

    upload_data = EvidenceUpload(
        report_id=report_id,
        file_type=file_type,
        encryption_metadata=enc_meta,
        file_hash_sha256=file_hash_sha256,
        original_filename=file.filename,
        mime_type=file.content_type,
        has_gps_metadata=has_gps_metadata,
        gps_latitude=gps_latitude,
        gps_longitude=gps_longitude,
        recorded_at=rec_at,
        offline_id=offline_id
    )

    try:
        evidence = await reporting_service.process_evidence_upload(
            db,
            current_user.id,
            upload_data,
            file_content
        )
        return to_evidence_file_response(evidence)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
