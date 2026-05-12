from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, allow_anonymous
from app.core.logging import security_logger
from app.models.user import User
from app.schemas.auth import (
    OTPRequest,
    OTPVerify,
    TokenResponse,
    AnonymousSessionCreate,
    AnonymousSessionResponse,
    UserResponse,
    UserUpdate,
    TrustedContactCreate,
    TrustedContactResponse,
    to_user_response,
    to_token_response,
    to_anonymous_session_response,
    to_trusted_contact_response,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import auth_service
from app.repositories.user import trusted_contact_repo, user_repo

router = APIRouter()


@router.post("/request-otp", response_model=dict)
async def request_otp(
    request: Request,
    data: OTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request OTP for phone number verification."""
    client_ip = request.client.host if request.client else None
    result = await auth_service.request_otp(db, data, ip=client_ip)
    return result


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    request: Request,
    data: OTPVerify,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and authenticate user."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    print(f"[DEBUG VERIFY] Payload received: phone_number={data.phone_number}, otp_code='{data.otp_code}', country_code={data.country_code}", flush=True)

    try:
        access_token, refresh_token, expires_in, user = await auth_service.verify_otp(
            db, data, ip=client_ip, user_agent=user_agent
        )
        return to_token_response(access_token, refresh_token, expires_in, user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/anonymous", response_model=AnonymousSessionResponse)
async def create_anonymous_session(
    request: Request,
    data: AnonymousSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create anonymous session for unauthenticated access."""
    client_ip = request.client.host if request.client else None
    session_token, user, expires_at = await auth_service.create_anonymous_session(
        db, data, ip=client_ip
    )
    return to_anonymous_session_response(session_token, user, expires_at)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    try:
        access_token, new_refresh_token, expires_in, user_dict = await auth_service.refresh_token(refresh_token)
        # For refresh token, we create response directly since user is not from ORM
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=expires_in,
            user=UserResponse(**user_dict)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user information."""
    return to_user_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile."""
    update_data = data.model_dump(exclude_unset=True)
    await user_repo.update(db, current_user, update_data)
    # Reload user with trusted_contacts eager-loaded for response
    updated = await user_repo.get_by_id(db, current_user.id)
    return to_user_response(updated)


# Trusted Contacts

@router.get("/trusted-contacts", response_model=list[TrustedContactResponse])
async def get_trusted_contacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's trusted contacts."""
    contacts = await trusted_contact_repo.get_by_user(db, current_user.id)
    return [to_trusted_contact_response(c) for c in contacts]


@router.post("/trusted-contacts", response_model=TrustedContactResponse)
async def add_trusted_contact(
    data: TrustedContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a trusted contact."""
    contact_data = data.model_dump()
    contact_data["user_id"] = current_user.id

    contact = await trusted_contact_repo.create(db, contact_data)
    return to_trusted_contact_response(contact)


@router.delete("/trusted-contacts/{contact_id}")
async def remove_trusted_contact(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a trusted contact."""
    from uuid import UUID

    # Verify ownership
    contacts = await trusted_contact_repo.get_by_user(db, current_user.id)
    contact = next((c for c in contacts if str(c.id) == contact_id), None)

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    await trusted_contact_repo.delete(db, UUID(contact_id))
    return SuccessResponse(message="Contact removed successfully")
