import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional,TYPE_CHECKING

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User

class ReportStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class ReportType(str, Enum):
    ASSAULT = "assault"
    HARASSMENT = "harassment"
    DOMESTIC_VIOLENCE = "domestic_violence"
    STALKING = "stalking"
    THREAT = "threat"
    OTHER = "other"


class EvidenceType(str, Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    TEXT = "text"


class IncidentReport(SQLModel, table=True):
    __tablename__ = "incident_reports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL"), index=True))

    # Report details
    report_number: str = Field(max_length=20, unique=True, index=True)
    report_type: str = Field(max_length=30, index=True)
    status: str = Field(default=ReportStatus.SUBMITTED, max_length=30, index=True)

    # Incident details
    incident_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    incident_latitude: Optional[float] = Field(default=None)
    incident_longitude: Optional[float] = Field(default=None)
    incident_address: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Anonymous reporting support
    is_anonymous: bool = Field(default=False, index=True)
    reporter_age_range: Optional[str] = Field(default=None, max_length=20)  # 18-24, 25-34, etc.
    reporter_gender: Optional[str] = Field(default=None, max_length=20)

    # Content (encrypted on client before sending)
    description_encrypted: Optional[str] = Field(default=None, sa_column=Column(Text))  # Base64 encrypted description
    encryption_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # Algorithm, key id, etc.

    # Follow-up preferences (for non-anonymous)
    follow_up_preference: str = Field(default="none", max_length=20)  # none, email, phone, lawyer
    contact_email_encrypted: Optional[str] = Field(default=None, sa_column=Column(Text))
    contact_phone_encrypted: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Metadata
    submitted_from_ip: Optional[str] = Field(default=None, max_length=45)
    submitted_from_device: Optional[str] = Field(default=None, max_length=64)

    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    # Sync fields
    client_created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    sync_status: str = Field(default="synced", max_length=20)
    offline_id: Optional[str] = Field(default=None, max_length=64, index=True)

    # Relationships
    user: Optional["User"] = Relationship(
        back_populates="incident_reports",
        sa_relationship_kwargs={"foreign_keys": "IncidentReport.user_id"}
    )
    evidence_files: List["EvidenceFile"] = Relationship(
        back_populates="report",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "foreign_keys": "EvidenceFile.report_id"}
    )

    def __repr__(self):
        return f"<IncidentReport(id={self.id}, report_number={self.report_number}, status={self.status})>"


class EvidenceFile(SQLModel, table=True):
    __tablename__ = "evidence_files"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    report_id: uuid.UUID = Field(sa_column=Column(ForeignKey("incident_reports.id", ondelete="CASCADE"), index=True))
    uploaded_by: Optional[uuid.UUID] = Field(default=None, sa_column=Column(ForeignKey("users.id", ondelete="SET NULL")))

    # File metadata
    file_type: str = Field(max_length=20, index=True)  # image, audio, video
    original_filename: Optional[str] = Field(default=None, max_length=255)  # For reference only
    mime_type: Optional[str] = Field(default=None, max_length=100)
    file_size_bytes: Optional[int] = Field(default=None)

    # Storage - file is encrypted, we store reference only
    storage_provider: str = Field(default="local", max_length=20)  # local, s3, gcs
    storage_path: str = Field(sa_column=Column(Text))  # Path or key to encrypted file
    storage_bucket: Optional[str] = Field(default=None, max_length=100)

    # Encryption
    file_encryption_key_encrypted: Optional[str] = Field(default=None, sa_column=Column(Text))  # DEK encrypted with KEK
    encryption_iv: Optional[str] = Field(default=None, max_length=64)  # Initialization vector
    encryption_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Verification
    file_hash_sha256: Optional[str] = Field(default=None, max_length=64)  # Hash of encrypted content
    file_hash_original: Optional[str] = Field(default=None, max_length=64)  # Hash of original (for dedup)

    # Thumbnails (for images)
    thumbnail_path: Optional[str] = Field(default=None, sa_column=Column(Text))
    thumbnail_encrypted: bool = Field(default=True)

    # Metadata extraction
    extracted_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # EXIF, audio metadata (stripped of PII)
    has_gps_metadata: bool = Field(default=False)
    gps_latitude: Optional[float] = Field(default=None)
    gps_longitude: Optional[float] = Field(default=None)

    # Processing status
    processing_status: str = Field(default="pending", max_length=20)  # pending, processing, complete, error
    processing_error: Optional[str] = Field(default=None, sa_column=Column(Text))
    virus_scan_status: str = Field(default="pending", max_length=20)  # pending, clean, infected

    # Timestamps
    recorded_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))  # When evidence was captured
    uploaded_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Sync fields
    client_uploaded_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    offline_id: Optional[str] = Field(default=None, max_length=64, index=True)

    # Relationships
    report: "IncidentReport" = Relationship(
        back_populates="evidence_files",
        sa_relationship_kwargs={"foreign_keys": "EvidenceFile.report_id"}
    )

    def __repr__(self):
        return f"<EvidenceFile(id={self.id}, type={self.file_type}, report_id={self.report_id})>"
