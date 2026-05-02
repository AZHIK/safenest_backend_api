from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupportCenterNearbyRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(default=10.0, ge=0.1, le=100)
    center_types: List[str] = Field(default_factory=list)
    is_24_7: Optional[bool] = None
    provides_medical: Optional[bool] = None
    provides_legal: Optional[bool] = None
    provides_shelter: Optional[bool] = None


class SupportCenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    center_type: str
    category_tags: Optional[str]

    address: str
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]

    latitude: float
    longitude: float
    distance_km: Optional[float] = None

    phone_primary: Optional[str]
    phone_emergency: Optional[str]
    email: Optional[str]
    website: Optional[str]

    is_24_7: bool
    operating_hours: Optional[str]
    languages_supported: Optional[str]

    provides_medical: bool
    provides_legal: bool
    provides_shelter: bool
    provides_counseling: bool
    provides_emergency_response: bool
    provides_anonymous_support: bool

    wheelchair_accessible: bool
    gender_specific: Optional[str]

    is_verified: bool
    rating_average: float
    rating_count: int

    is_active: bool


# Mapper functions for safe ORM -> Schema conversion
# These must be called ONLY after all relationships are eagerly loaded

def to_support_center_response(center) -> SupportCenterResponse:
    """Convert SupportCenter ORM to response schema."""
    return SupportCenterResponse(
        id=center.id,
        name=center.name,
        center_type=center.center_type,
        category_tags=center.category_tags,
        address=center.address,
        city=center.city,
        state=center.state,
        country=center.country,
        postal_code=center.postal_code,
        latitude=center.latitude,
        longitude=center.longitude,
        distance_km=getattr(center, 'distance_km', None),
        phone_primary=center.phone_primary,
        phone_emergency=center.phone_emergency,
        email=center.email,
        website=center.website,
        is_24_7=center.is_24_7,
        operating_hours=center.operating_hours,
        languages_supported=center.languages_supported,
        provides_medical=center.provides_medical,
        provides_legal=center.provides_legal,
        provides_shelter=center.provides_shelter,
        provides_counseling=center.provides_counseling,
        provides_emergency_response=center.provides_emergency_response,
        provides_anonymous_support=center.provides_anonymous_support,
        wheelchair_accessible=center.wheelchair_accessible,
        gender_specific=center.gender_specific,
        is_verified=center.is_verified,
        rating_average=center.rating_average,
        rating_count=center.rating_count,
        is_active=center.is_active
    )
