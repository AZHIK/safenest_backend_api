import re
from typing import Optional


def validate_phone_number(phone: str, country_code: str = "+1") -> tuple[bool, str]:
    """Validate phone number format."""
    digits = "".join(c for c in phone if c.isdigit())

    if len(digits) < 8:
        return False, "Phone number must have at least 8 digits"

    if len(digits) > 15:
        return False, "Phone number too long"

    # Validate country code format
    if not re.match(r"^\+[1-9]\d{0,3}$", country_code):
        return False, "Invalid country code format"

    return True, f"{country_code}{digits}"


def sanitize_text(text: Optional[str], max_length: int = 1000) -> Optional[str]:
    """Sanitize text input by removing potentially dangerous characters."""
    if not text:
        return None

    # Remove null bytes
    text = text.replace("\x00", "")

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    # Basic XSS prevention
    text = text.replace("<", "&lt;").replace(">", "&gt;")

    return text.strip()


def validate_coordinates(lat: float, lng: float) -> tuple[bool, str]:
    """Validate geographic coordinates."""
    if not (-90 <= lat <= 90):
        return False, "Latitude must be between -90 and 90"

    if not (-180 <= lng <= 180):
        return False, "Longitude must be between -180 and 180"

    return True, "Valid"


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def normalize_phone(phone: str) -> str:
    """Normalize phone number to digits only."""
    return "".join(c for c in phone if c.isdigit())
