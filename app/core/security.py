import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing context (for future use if needed)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def verify_token_type(token: str, expected_type: str) -> Optional[dict]:
    payload = decode_token(token)
    if payload is None:
        return None
    token_type = payload.get("type")
    if token_type != expected_type:
        return None
    return payload


def generate_otp(length: int = None) -> str:
    length = length or settings.otp_length
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def generate_anonymous_session_id() -> str:
    return f"anon_{secrets.token_urlsafe(32)}"


def generate_secure_id(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


class TokenManager:
    @staticmethod
    def create_token_pair(user_id: str, phone_number: str, is_anonymous: bool = False) -> Tuple[str, str]:
        token_data = {
            "sub": user_id,
            "phone": phone_number,
            "anonymous": is_anonymous
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        return access_token, refresh_token

    @staticmethod
    def verify_access_token(token: str) -> Optional[dict]:
        return verify_token_type(token, "access")

    @staticmethod
    def verify_refresh_token(token: str) -> Optional[dict]:
        return verify_token_type(token, "refresh")


token_manager = TokenManager()
