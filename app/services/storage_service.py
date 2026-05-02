import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import aiofiles

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class StorageService:
    """
    Storage service abstraction for encrypted evidence files.
    Currently implements local storage; S3 integration is prepared.
    """

    def __init__(self):
        self.provider = "local"
        self.bucket_name = settings.s3_bucket_name or "safenest-local"
        self.upload_dir = Path(settings.upload_dir)
        self.temp_dir = Path(settings.temp_upload_dir)

        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def store_evidence(
        self,
        file_content: bytes,
        file_type: str,
        file_hash: str,
        mime_type: str
    ) -> str:
        """Store encrypted evidence file and return storage path."""

        # Generate unique path
        date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        filename = f"{uuid4().hex}_{file_hash[:16]}"

        if file_type == "image":
            subdir = "images"
        elif file_type == "audio":
            subdir = "audio"
        elif file_type == "video":
            subdir = "video"
        else:
            subdir = "documents"

        storage_path = f"{subdir}/{date_prefix}/{filename}"
        full_path = self.upload_dir / storage_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_content)

        logger.info(
            "evidence_stored",
            provider=self.provider,
            path=storage_path,
            size_bytes=len(file_content)
        )

        return storage_path

    async def store_temp(self, file_content: bytes, original_filename: str) -> str:
        """Store file temporarily during upload processing."""
        temp_id = uuid4().hex
        temp_path = self.temp_dir / f"{temp_id}_{original_filename}"

        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(file_content)

        return str(temp_path)

    async def delete_temp(self, temp_path: str) -> bool:
        """Delete temporary file."""
        try:
            os.unlink(temp_path)
            return True
        except Exception:
            return False

    async def get_file(self, storage_path: str) -> Optional[bytes]:
        """Retrieve file content."""
        full_path = self.upload_dir / storage_path

        if not full_path.exists():
            return None

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def get_presigned_url(
        self,
        storage_path: str,
        expires_seconds: int = 3600
    ) -> str:
        """Generate presigned URL for file access.

        For local storage, returns a local path that requires API access.
        For S3, would return actual presigned URL.
        """
        if settings.s3_enabled:
            # TODO: Implement S3 presigned URL generation
            pass

        # Local storage - return API endpoint path
        return f"/api/v1/evidence/download/{storage_path}"

    async def delete_file(self, storage_path: str) -> bool:
        """Delete stored file."""
        full_path = self.upload_dir / storage_path

        try:
            if full_path.exists():
                os.unlink(full_path)
            return True
        except Exception as e:
            logger.error("delete_failed", path=storage_path, error=str(e))
            return False

    async def get_file_info(self, storage_path: str) -> Optional[dict]:
        """Get file metadata."""
        full_path = self.upload_dir / storage_path

        if not full_path.exists():
            return None

        stat = full_path.stat()
        return {
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        }


class S3StorageService(StorageService):
    """Future S3 implementation placeholder."""

    def __init__(self):
        super().__init__()
        self.provider = "s3"
        self.bucket_name = settings.s3_bucket_name

        # TODO: Initialize boto3 client
        # self.s3_client = boto3.client(
        #     's3',
        #     aws_access_key_id=settings.aws_access_key_id,
        #     aws_secret_access_key=settings.aws_secret_access_key,
        #     region_name=settings.aws_region
        # )

    async def store_evidence(
        self,
        file_content: bytes,
        file_type: str,
        file_hash: str,
        mime_type: str
    ) -> str:
        # TODO: Implement S3 upload with server-side encryption
        # For now, fall back to local storage
        return await super().store_evidence(file_content, file_type, file_hash, mime_type)

    async def get_presigned_url(
        self,
        storage_path: str,
        expires_seconds: int = 3600
    ) -> str:
        # TODO: Generate actual S3 presigned URL
        pass


def get_storage_service() -> StorageService:
    """Factory function to get appropriate storage service."""
    if settings.s3_enabled:
        return S3StorageService()
    return StorageService()


# Global instance
storage_service = get_storage_service()
