"""
Operator Authentication API Routes

Separate authentication system for institutional operators.

- POST /api/v1/operator/auth/login
- POST /api/v1/operator/auth/refresh
- GET /api/v1/operator/auth/me
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import security_logger, get_logger
from app.operator_auth import get_current_operator, get_optional_operator
from app.operator_models.operator import OperatorUser
from app.operator_repositories.operator_user import operator_user_repo
from app.operator_schemas.auth import (
    OperatorLoginRequest,
    OperatorRegisterRequest,
    OperatorTokenResponse,
    OperatorTokenRefreshRequest,
    OperatorMeResponse,
    OperatorPasswordChangeRequest,
    OperatorPasswordResetRequest,
)
from app.operator_services.operator_auth_service import operator_auth_service
from app.operator_services.operator_user_service import operator_user_service
from app.operator_schemas.operator_user import OperatorUserCreate

logger = get_logger(__name__)
router = APIRouter()


def _mask_email(email: str) -> str:
    local, separator, domain = email.partition("@")
    if not separator:
        return "****"

    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}****@{domain}"


def _to_me_response(user: OperatorUser) -> OperatorMeResponse:
    """Convert OperatorUser to OperatorMeResponse."""
    role_names = []
    if user.role_links:
        role_names = [link.role.name for link in user.role_links if link.role]
    
    return OperatorMeResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        is_super_admin=user.is_super_admin,
        email_verified=user.email_verified,
        last_login=user.last_login,
        created_at=user.created_at,
        setup_completed=user.setup_completed,
        roles=role_names
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
async def register(
    data: OperatorRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Self-registration endpoint for operators.
    
    Creates a new operator account. In production, this account 
    would need verification/approval before full access.
    """
    # Convert RegisterRequest to UserCreate
    user_create = OperatorUserCreate(
        full_name=data.full_name,
        email=data.email,
        password=data.password,
        phone=data.phone,
        is_active=True,  # Default to active for now
        is_super_admin=False,
        role_ids=[]
    )
    
    user, message = await operator_user_service.create_user(db, user_create)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {
        "message": "Operator registered successfully. Please contact an administrator to assign roles.",
        "user_id": str(user.id)
    }


@router.post(
    "/login",
    response_model=OperatorTokenResponse,
    status_code=status.HTTP_200_OK
)
async def login(
    request: Request,
    data: OperatorLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Operator login endpoint.
    
    Authenticates operator credentials and returns JWT tokens.
    Separate from survivor mobile app authentication.
    """
    # Check rate limiting (simple implementation)
    # In production, use proper rate limiting middleware
    
    client_host = request.client.host if request.client else None
    masked_email = _mask_email(data.email)

    try:
        token_response = await operator_auth_service.login(
            db, data.email, data.password
        )
    except Exception:
        logger.exception(
            "operator_login_error",
            email=masked_email,
            client_ip=client_host,
            path=request.url.path,
            method=request.method,
        )
        raise
    
    if not token_response:
        security_logger.log_suspicious_activity(
            ip=client_host,
            activity="operator_login_failed",
        )
        logger.warning(
            "operator_login_failed",
            email=masked_email,
            client_ip=client_host,
            path=request.url.path,
            method=request.method,
            reason="invalid_credentials_or_account_state",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_response


@router.post(
    "/refresh",
    response_model=OperatorTokenResponse,
    status_code=status.HTTP_200_OK
)
async def refresh_token(
    data: OperatorTokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh operator access token.
    
    Uses valid refresh token to generate new access and refresh tokens.
    """
    token_response = await operator_auth_service.refresh_token(
        db, data.refresh_token
    )
    
    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT
)
async def logout(
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """
    Logout operator and revoke tokens.
    """
    # Get current JTI from user
    jti = current_user.current_jti
    
    await operator_auth_service.logout(db, current_user.id, jti)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=OperatorMeResponse,
    status_code=status.HTTP_200_OK
)
async def get_current_operator_profile(
    current_user: OperatorUser = Depends(get_current_operator)
):
    """
    Get current operator's profile.
    
    Returns operator information including assigned roles.
    """
    return _to_me_response(current_user)


@router.put(
    "/me/password",
    status_code=status.HTTP_200_OK
)
async def change_password(
    data: OperatorPasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """
    Change current operator's password.
    
    Requires current password verification.
    Logs out all existing sessions.
    """
    # Validate password confirmation
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )
    
    success, message = await operator_auth_service.change_password(
        db,
        current_user.id,
        data.current_password,
        data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"message": message}


@router.post(
    "/password-reset-request",
    status_code=status.HTTP_200_OK
)
async def request_password_reset(
    data: OperatorPasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset.
    
    In production: Sends email with reset link.
    For now: Logs the request (actual email sending to be implemented).
    """
    user = await operator_user_repo.get_by_email(db, data.email)
    
    if user:
        # Generate reset token (expires in 1 hour)
        from datetime import datetime, timezone, timedelta
        import secrets
        
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        
        await operator_auth_service.set_password_reset_token(db, user.id, token, expires)
        
        # TODO: Send email with reset link
        logger.info(
            "password_reset_requested",
            user_id=str(user.id),
            email=data.email
        )
        
        # In development, return token for testing
        # In production, do NOT return the token
        return {
            "message": "Password reset instructions sent to email",
            "debug_token": token  # Remove in production
        }
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, password reset instructions have been sent"}
