from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.reporting import evidence_file_repo, incident_report_repo
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("/download/{storage_path:path}")
async def download_evidence(
    storage_path: str,
    evidence_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download/View evidence file.
    
    For encrypted files, this endpoint serves the encrypted content.
    The client (admin dashboard) should handle decryption if needed.
    """
    # If evidence_id is provided, verify access
    if evidence_id:
        evidence = await evidence_file_repo.get_by_id(db, evidence_id)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence not found"
            )
        
        # Verify report access (operator/stakeholder can view)
        report = await incident_report_repo.get_by_id(db, evidence.report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # For now, allow all authenticated operators to view evidence
        # In production, add proper permission checks
    
    # Retrieve file from storage
    file_content = await storage_service.get_file(storage_path)
    
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage"
        )
    
    # Determine content type based on storage path
    content_type = "application/octet-stream"
    if storage_path.startswith("images/"):
        content_type = "image/jpeg"
    elif storage_path.startswith("audio/"):
        content_type = "audio/m4a"
    elif storage_path.startswith("video/"):
        content_type = "video/mp4"
    elif storage_path.startswith("documents/"):
        content_type = "application/pdf"
    
    return Response(
        content=file_content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename=evidence_{storage_path.split('/')[-1]}",
            "Cache-Control": "private, max-age=3600",
        }
    )
