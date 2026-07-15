from pathlib import PurePosixPath
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_user
from app.models.user import User
from app.operator_auth import get_optional_operator
from app.operator_models.operator import OperatorUser
from app.repositories.reporting import evidence_file_repo, incident_report_repo
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("/download/{storage_path:path}")
async def download_evidence(
    storage_path: str,
    evidence_id: Optional[UUID] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
    current_operator: Optional[OperatorUser] = Depends(get_optional_operator),
    db: AsyncSession = Depends(get_db),
):
    """
    Download/View evidence file.
    
    For encrypted files, this endpoint serves the encrypted content.
    The client (admin dashboard) should handle decryption if needed.
    """
    if not current_user and not current_operator:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    resolved_evidence = None

    # If evidence_id is provided, verify access
    if evidence_id:
        resolved_evidence = await evidence_file_repo.get_by_id(db, evidence_id)
        if not resolved_evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found"
            )

        # Verify report access (operator/stakeholder can view)
        report = await incident_report_repo.get_by_id(db, resolved_evidence.report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        if current_operator:
            # Operator permission checks are handled by operator auth/token issuance.
            pass
        elif current_user:
            if report.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to view this evidence"
                )

    resolved_storage_path = storage_path
    file_content = await storage_service.get_file(resolved_storage_path)

    if not file_content:
        legacy_filename = PurePosixPath(storage_path).name
        if legacy_filename:
            resolved_evidence = resolved_evidence or await evidence_file_repo.get_by_original_filename(
                db, legacy_filename
            )
            if resolved_evidence:
                resolved_storage_path = resolved_evidence.storage_path
                file_content = await storage_service.get_file(resolved_storage_path)

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage"
        )

    # Determine content type based on evidence metadata first, then storage path
    content_type = (
        resolved_evidence.mime_type
        if resolved_evidence and resolved_evidence.mime_type
        else "application/octet-stream"
    )
    if content_type == "application/octet-stream":
        if resolved_storage_path.startswith("images/"):
            content_type = "image/jpeg"
        elif resolved_storage_path.startswith("audio/"):
            content_type = "audio/m4a"
        elif resolved_storage_path.startswith("video/"):
            content_type = "video/mp4"
        elif resolved_storage_path.startswith("documents/"):
            content_type = "application/pdf"

    filename = (
        resolved_evidence.original_filename
        if resolved_evidence and resolved_evidence.original_filename
        else f"evidence_{resolved_storage_path.split('/')[-1]}"
    )

    return Response(
        content=file_content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Cache-Control": "private, max-age=3600",
        }
    )
