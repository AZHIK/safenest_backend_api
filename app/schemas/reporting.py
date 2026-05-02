from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentReportCreate(BaseModel):
    report_type: str = Field(..., pattern=r"^(assault|harassment|domestic_violence|stalking|threat|other)$")

    # Incident details
    incident_date: Optional[datetime] = None
    incident_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    incident_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    incident_address: Optional[str] = Field(default=None, max_length=500)

    # Encrypted content (client-encrypted)
    description_encrypted: str = Field(..., min_length=1)
    encryption_metadata: dict = Field(...)

    # Anonymous options
    is_anonymous: bool = False
    reporter_age_range: Optional[str] = Field(default=None, pattern=r"^(18-24|25-34|35-44|45-54|55-64|65+|prefer_not_say)$")
    reporter_gender: Optional[str] = None

    # Follow-up (encrypted if provided)
    follow_up_preference: str = Field(default="none")
    contact_email_encrypted: Optional[str] = None
    contact_phone_encrypted: Optional[str] = None

    # Offline support
    client_created_at: Optional[datetime] = None
    offline_id: Optional[str] = Field(default=None, max_length=64)


class IncidentReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_number: str
    report_type: str
    status: str
    is_anonymous: bool
    incident_date: Optional[datetime]
    incident_latitude: Optional[float]
    incident_longitude: Optional[float]
    encryption_metadata: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]
    client_created_at: Optional[datetime]
    offline_id: Optional[str]


class EvidenceUpload(BaseModel):
    report_id: UUID
    file_type: str = Field(..., pattern=r"^(image|audio|video|document)$")
    encryption_metadata: dict = Field(...)
    file_hash_sha256: str
    original_filename: Optional[str] = Field(default=None, max_length=255)
    mime_type: str
    recorded_at: Optional[datetime] = None
    has_gps_metadata: bool = False
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    offline_id: Optional[str] = Field(default=None, max_length=64)


class EvidenceFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_id: UUID
    file_type: str
    mime_type: str
    file_size_bytes: int
    storage_path: str
    encryption_metadata: Optional[dict]
    file_hash_sha256: str
    has_gps_metadata: bool
    processing_status: str
    virus_scan_status: str
    uploaded_at: datetime
    thumbnail_path: Optional[str]
    offline_id: Optional[str]


class ReportWithEvidenceResponse(IncidentReportResponse):
    evidence_files: List[EvidenceFileResponse] = []


# Mapper functions for safe ORM -> Schema conversion
# These must be called ONLY after all relationships are eagerly loaded

def to_evidence_file_response(evidence) -> EvidenceFileResponse:
    """Convert EvidenceFile ORM to response schema."""
    return EvidenceFileResponse(
        id=evidence.id,
        report_id=evidence.report_id,
        file_type=evidence.file_type,
        mime_type=evidence.mime_type,
        file_size_bytes=evidence.file_size_bytes,
        storage_path=evidence.storage_path,
        encryption_metadata=evidence.encryption_metadata,
        file_hash_sha256=evidence.file_hash_sha256,
        has_gps_metadata=evidence.has_gps_metadata,
        processing_status=evidence.processing_status,
        virus_scan_status=evidence.virus_scan_status,
        uploaded_at=evidence.uploaded_at,
        thumbnail_path=evidence.thumbnail_path,
        offline_id=evidence.offline_id
    )


def to_incident_report_response(report) -> IncidentReportResponse:
    """Convert IncidentReport ORM to response schema."""
    return IncidentReportResponse(
        id=report.id,
        report_number=report.report_number,
        report_type=report.report_type,
        status=report.status,
        is_anonymous=report.is_anonymous,
        incident_date=report.incident_date,
        incident_latitude=report.incident_latitude,
        incident_longitude=report.incident_longitude,
        encryption_metadata=report.encryption_metadata,
        created_at=report.created_at,
        updated_at=report.updated_at,
        client_created_at=report.client_created_at,
        offline_id=report.offline_id
    )


def to_report_with_evidence_response(report) -> ReportWithEvidenceResponse:
    """Convert IncidentReport ORM with evidence_files to response schema."""
    return ReportWithEvidenceResponse(
        id=report.id,
        report_number=report.report_number,
        report_type=report.report_type,
        status=report.status,
        is_anonymous=report.is_anonymous,
        incident_date=report.incident_date,
        incident_latitude=report.incident_latitude,
        incident_longitude=report.incident_longitude,
        encryption_metadata=report.encryption_metadata,
        created_at=report.created_at,
        updated_at=report.updated_at,
        client_created_at=report.client_created_at,
        offline_id=report.offline_id,
        evidence_files=[
            to_evidence_file_response(e)
            for e in (getattr(report, 'evidence_files', None) or [])
        ]
    )
