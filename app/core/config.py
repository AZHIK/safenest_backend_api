import os
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    environment: str = Field(default="development", alias="ENVIRONMENT")
    app_name: str = Field(default="SafeNest API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.environment.lower() == "testing"

    # Database
    database_url: str = Field(alias="DATABASE_URL")
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(alias="REDIS_URL")
    redis_pool_size: int = Field(default=50, alias="REDIS_POOL_SIZE")

    # Celery
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")

    # JWT Security
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # OTP Security
    otp_expiry_minutes: int = Field(default=5, alias="OTP_EXPIRY_MINUTES")
    otp_length: int = Field(default=6, alias="OTP_LENGTH")

    # File Upload
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB")
    upload_dir: str = Field(default="uploads/evidence", alias="UPLOAD_DIR")
    temp_upload_dir: str = Field(default="uploads/temp", alias="TEMP_UPLOAD_DIR")
    allowed_image_types: str = Field(
        default="image/jpeg,image/png,image/webp,image/heic",
        alias="ALLOWED_IMAGE_TYPES"
    )
    allowed_audio_types: str = Field(
        default="audio/mpeg,audio/wav,audio/ogg,audio/mp4",
        alias="ALLOWED_AUDIO_TYPES"
    )

    @property
    def allowed_image_mime_types(self) -> List[str]:
        return [t.strip() for t in self.allowed_image_types.split(",")]

    @property
    def allowed_audio_mime_types(self) -> List[str]:
        return [t.strip() for t in self.allowed_audio_types.split(",")]

    @property
    def allowed_file_mime_types(self) -> List[str]:
        return self.allowed_image_mime_types + self.allowed_audio_mime_types

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    # Encryption
    encryption_key: str = Field(alias="ENCRYPTION_KEY")

    # Rate Limiting
    rate_limit_auth: int = Field(default=5, alias="RATE_LIMIT_AUTH")
    rate_limit_sos: int = Field(default=10, alias="RATE_LIMIT_SOS")
    rate_limit_general: int = Field(default=100, alias="RATE_LIMIT_GENERAL")

    # CORS
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",")]

    # AWS S3 (Optional)
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket_name: Optional[str] = Field(default=None, alias="S3_BUCKET_NAME")

    @property
    def s3_enabled(self) -> bool:
        return bool(self.aws_access_key_id and self.s3_bucket_name)

    # SMS/OTP Provider
    sms_provider: str = Field(default="twilio", alias="SMS_PROVIDER")
    twilio_account_sid: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(default=None, alias="TWILIO_PHONE_NUMBER")

    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")

    # WebSocket
    ws_heartbeat_interval: int = Field(default=30, alias="WS_HEARTBEAT_INTERVAL")
    ws_timeout: int = Field(default=300, alias="WS_TIMEOUT")

    @field_validator("jwt_secret_key", "encryption_key")
    @classmethod
    def validate_secret_length(cls, v: str, info) -> str:
        if len(v) < 32:
            raise ValueError(f"{info.field_name} must be at least 32 characters long")
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()
