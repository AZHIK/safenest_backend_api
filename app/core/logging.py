import logging
import sys
from typing import Any

import structlog

from app.core.config import get_settings

settings = get_settings()


def configure_logging() -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.is_production else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


class SecurityLogger:
    def __init__(self):
        self.logger = get_logger("security")

    def log_auth_attempt(self, phone: str, success: bool, ip: str = None, reason: str = None):
        self.logger.info(
            "authentication_attempt",
            phone=phone[:4] + "****" + phone[-4:] if len(phone) > 8 else "****",
            success=success,
            ip=ip,
            reason=reason
        )

    def log_sos_triggered(self, user_id: str, alert_id: str, lat: float = None, lng: float = None):
        self.logger.warning(
            "sos_triggered",
            user_id=user_id,
            alert_id=alert_id,
            location_available=lat is not None and lng is not None
        )

    def log_file_upload(self, user_id: str, file_type: str, success: bool, size: int = None):
        self.logger.info(
            "file_upload",
            user_id=user_id,
            file_type=file_type,
            success=success,
            size_bytes=size
        )

    def log_suspicious_activity(self, user_id: str = None, ip: str = None, activity: str = None, details: dict = None):
        extra = {
            "user_id": user_id,
            "ip": ip,
            "activity": activity,
        }
        if details:
            extra["details"] = details
        self.logger.warning("suspicious_activity", **extra)


security_logger = SecurityLogger()
