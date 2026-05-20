import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from sqlmodel import Field, SQLModel


class SupportCenterType(str, Enum):
    POLICE = "police"
    HOSPITAL = "hospital"
    NGO = "ngo"
    LEGAL_AID = "legal_aid"
    SHELTER = "shelter"
    HOTLINE = "hotline"
    COUNSELING = "counseling"


class SupportCenter(SQLModel, table=True):
    __tablename__ = "support_centers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Basic info
    name: str = Field(max_length=200)
    center_type: str = Field(max_length=30, index=True)
    category_tags: Optional[str] = Field(default=None, max_length=255)  # Comma-separated tags

    # Location
    address: str = Field(sa_column=Column(Text))
    city: Optional[str] = Field(default=None, max_length=100, index=True)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100, index=True)
    postal_code: Optional[str] = Field(default=None, max_length=20)

    latitude: float = Field(index=True)
    longitude: float = Field(index=True)
    geo_location: Optional[object] = Field(default=None, sa_column=Column(Geometry("POINT", srid=4326)))  # For spatial queries

    # Contact
    phone_primary: Optional[str] = Field(default=None, max_length=30)
    phone_emergency: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=100)
    website: Optional[str] = Field(default=None, max_length=255)

    # Availability
    is_24_7: bool = Field(default=False, index=True)
    operating_hours: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON or text description
    languages_supported: Optional[str] = Field(default=None, max_length=255)  # Comma-separated

    # Services
    provides_medical: bool = Field(default=False)
    provides_legal: bool = Field(default=False)
    provides_shelter: bool = Field(default=False)
    provides_counseling: bool = Field(default=False)
    provides_emergency_response: bool = Field(default=False)
    provides_anonymous_support: bool = Field(default=False)

    # Accessibility
    wheelchair_accessible: bool = Field(default=False)
    gender_specific: Optional[str] = Field(default=None, max_length=20)  # women, men, all, lgbtq
    age_restrictions: Optional[str] = Field(default=None, max_length=50)

    # Ratings and verification
    is_verified: bool = Field(default=False, index=True)
    verification_date: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    rating_average: float = Field(default=0.0)
    rating_count: int = Field(default=0)

    # Metadata
    source: Optional[str] = Field(default=None, max_length=50)  # government, ngo, community, verified
    data_quality_score: int = Field(default=0)  # 0-100

    # Active status
    is_active: bool = Field(default=True, index=True)
    temporarily_closed: bool = Field(default=False)
    closure_reason: Optional[str] = Field(default=None, max_length=100)

    created_at: datetime = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))
    last_verified_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Ownership
    operator_id: Optional[uuid.UUID] = Field(default=None, foreign_key="operator_users.id", index=True)

    def __repr__(self):
        return f"<SupportCenter(id={self.id}, name={self.name}, type={self.center_type})>"

    def to_geojson(self) -> dict:
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude]
            },
            "properties": {
                "id": str(self.id),
                "name": self.name,
                "type": self.center_type,
                "address": self.address,
                "phone": self.phone_primary,
                "is_24_7": self.is_24_7
            }
        }
