import math
from typing import Optional, Tuple

from geopy.distance import geodesic
from geopy.geocoders import Nominatim

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


def calculate_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float
) -> float:
    """Calculate distance between two coordinates in kilometers."""
    return geodesic((lat1, lng1), (lat2, lng2)).kilometers


def calculate_bearing(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float
) -> float:
    """Calculate bearing from point 1 to point 2 in degrees."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    diff_lng = math.radians(lng2 - lng1)

    x = math.sin(diff_lng) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(diff_lng))

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def get_bounding_box(
    lat: float,
    lng: float,
    radius_km: float
) -> Tuple[float, float, float, float]:
    """Get bounding box for a radius around a point."""
    # Approximate degrees per km
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * max(abs(math.cos(math.radians(lat))), 0.01))

    return (
        lat - lat_delta,  # min_lat
        lat + lat_delta,  # max_lat
        lng - lng_delta,  # min_lng
        lng + lng_delta   # max_lng
    )


def get_address_from_coords(lat: float, lng: float) -> Optional[str]:
    """Reverse geocode coordinates to address."""
    if not settings.is_testing:
        try:
            geolocator = Nominatim(user_agent="safenest-api")
            location = geolocator.reverse(f"{lat}, {lng}")
            return location.address if location else None
        except Exception as e:
            logger.error("geocoding_error", error=str(e), lat=lat, lng=lng)
    return None


def format_coordinates(lat: float, lng: float, precision: int = 6) -> str:
    """Format coordinates as a readable string."""
    lat_dir = "N" if lat >= 0 else "S"
    lng_dir = "E" if lng >= 0 else "W"
    return f"{abs(lat):.{precision}f}°{lat_dir}, {abs(lng):.{precision}f}°{lng_dir}"


def is_within_radius(
    center_lat: float,
    center_lng: float,
    point_lat: float,
    point_lng: float,
    radius_km: float
) -> bool:
    """Check if a point is within radius of center."""
    distance = calculate_distance(center_lat, center_lng, point_lat, point_lng)
    return distance <= radius_km
