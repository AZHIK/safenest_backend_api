"""
Operator Mobile Users Management API Routes

- GET /api/v1/operator/mobile-users - List mobile users with pagination and search
- GET /api/v1/operator/mobile-users/{id} - Get detailed mobile user profile
- PATCH /api/v1/operator/mobile-users/{id}/status - Update mobile user status
- DELETE /api/v1/operator/mobile-users/{id} - Delete mobile user
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import get_db
from app.operator_auth import require_operator_permission, get_current_operator
from app.operator_models.operator import OperatorUser
from app.models.user import User as MobileUser, UserStatus
from app.models.reporting import IncidentReport
from app.repositories.user import user_repo
from app.repositories.sos import sos_alert_repo
from app.schemas.auth import UserResponse, TrustedContactResponse, to_user_response, to_trusted_contact_response
from app.schemas.sos import SOSResponse, to_sos_response
from app.schemas.reporting import IncidentReportResponse, to_incident_report_response

router = APIRouter()


# --- Pydantic Schemas for Responses ---

class ActivityItem(BaseModel):
    id: str
    type: str  # auth, sos, report, contact
    title: str
    description: str
    timestamp: datetime
    meta: Optional[dict] = None


class MobileUserDetailResponse(BaseModel):
    id: UUID
    phone_number: Optional[str]
    country_code: Optional[str]
    is_anonymous: bool
    is_verified: bool
    status: str
    nickname: Optional[str]
    language_preference: str
    emergency_message_template: Optional[str]
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    trusted_contacts: List[TrustedContactResponse]
    sos_alerts: List[SOSResponse]
    incident_reports: List[IncidentReportResponse]
    activity_log: List[ActivityItem]


class MobileUserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


class MobileUserStatusUpdate(BaseModel):
    status: str  # active, inactive, suspended


# --- Endpoint Route Handlers ---

@router.get(
    "",
    response_model=MobileUserListResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_operator_permission("users.view"))]
)
async def list_mobile_users(
    is_anonymous: Optional[bool] = Query(default=None),
    is_verified: Optional[bool] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List mobile app users with pagination, sorting, and filtering.
    """
    offset = (page - 1) * page_size
    query = select(MobileUser)

    # Apply filters
    filters = []
    if is_anonymous is not None:
        filters.append(MobileUser.is_anonymous == is_anonymous)
    if is_verified is not None:
        filters.append(MobileUser.is_verified == is_verified)
    if status is not None:
        filters.append(MobileUser.status == status)
    
    if search:
        # Search by phone number or nickname (using ILIKE/like)
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                MobileUser.phone_number.like(search_pattern),
                MobileUser.nickname.ilike(search_pattern)
            )
        )

    if filters:
        query = query.where(and_(*filters))

    # Get total count before limiting
    # Simple count execution
    from sqlalchemy import func
    total_count_query = select(func.count(MobileUser.id))
    if filters:
        total_count_query = total_count_query.where(and_(*filters))
    
    total_res = await db.execute(total_count_query)
    total = total_res.scalar() or 0

    # Paginate and sort
    query = query.order_by(desc(MobileUser.created_at)).offset(offset).limit(page_size)
    
    # Eager load trusted contacts for serialization using selectinload
    from sqlalchemy.orm import selectinload
    query = query.options(selectinload(MobileUser.trusted_contacts))

    result = await db.execute(query)
    users = result.scalars().all()

    # Map to schema response
    items = [to_user_response(user) for user in users]
    pages = (total + page_size - 1) // page_size

    return MobileUserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get(
    "/{user_id}",
    response_model=MobileUserDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_operator_permission("users.view"))]
)
async def get_mobile_user_details(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive details for a specific mobile user.
    Includes profile, trusted contacts, recent SOS alerts, incident reports, and a timeline.
    """
    # Fetch User along with trusted contacts
    from sqlalchemy.orm import selectinload
    user_result = await db.execute(
        select(MobileUser)
        .options(selectinload(MobileUser.trusted_contacts))
        .where(MobileUser.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mobile user not found"
        )

    # Fetch SOS Alerts (recent 20)
    alerts = await sos_alert_repo.get_recent_for_user(db, user_id, limit=20)

    # Fetch Incident Reports (recent 20)
    reports_result = await db.execute(
        select(IncidentReport)
        .where(IncidentReport.user_id == user_id)
        .order_by(desc(IncidentReport.created_at))
        .limit(20)
    )
    reports = reports_result.scalars().all()

    # Build Unified Chronological Activity Log (Timeline)
    activities: List[ActivityItem] = []

    # 1. Account Creation
    activities.append(
        ActivityItem(
            id=f"create-{user.id}",
            type="auth",
            title="Account Created",
            description=f"Initial registration as {'Anonymous Session' if user.is_anonymous else 'Verified User'}.",
            timestamp=user.created_at,
            meta={"is_anonymous": user.is_anonymous}
        )
    )

    # 2. Last Login Action (if available)
    if user.last_login_at:
        activities.append(
            ActivityItem(
                id=f"login-{user.id}",
                type="auth",
                title="Account Login",
                description="Logged in to the mobile application.",
                timestamp=user.last_login_at
            )
        )

    # 3. Trusted Contacts Actions
    for contact in user.trusted_contacts:
        activities.append(
            ActivityItem(
                id=f"contact-{contact.id}",
                type="contact",
                title="Added Trusted Contact",
                description=f"Added {contact.name} ({contact.relationship or 'Contact'}) as a trusted emergency contact.",
                timestamp=contact.created_at,
                meta={
                    "name": contact.name,
                    "phone": contact.phone_number,
                    "relationship": contact.relationship,
                    "priority": contact.priority
                }
            )
        )

    # 4. SOS Alerts Actions
    for alert in alerts:
        activities.append(
            ActivityItem(
                id=f"sos-{alert.id}",
                type="sos",
                title="Triggered SOS Alert",
                description=f"Emergency alert triggered via {alert.alert_type} (Status: {alert.status}). Notified {alert.contacts_notified} contacts.",
                timestamp=alert.created_at,
                meta={
                    "alert_id": str(alert.id),
                    "status": alert.status,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "contacts_notified": alert.contacts_notified
                }
            )
        )

    # 5. Incident Reports Actions
    for report in reports:
        activities.append(
            ActivityItem(
                id=f"report-{report.id}",
                type="report",
                title="Submitted Incident Report",
                description=f"Filed incident report #{report.report_number} for {report.report_type} (Status: {report.status}).",
                timestamp=report.created_at,
                meta={
                    "report_id": str(report.id),
                    "report_number": report.report_number,
                    "report_type": report.report_type,
                    "status": report.status
                }
            )
        )

    # Sort activities by timestamp descending
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    # Map models to Response schemas safely
    trusted_contacts_res = [to_trusted_contact_response(c) for c in user.trusted_contacts]
    sos_alerts_res = [to_sos_response(a) for a in alerts]
    incident_reports_res = [to_incident_report_response(r) for r in reports]

    return MobileUserDetailResponse(
        id=user.id,
        phone_number=user.phone_number,
        country_code=user.country_code,
        is_anonymous=user.is_anonymous,
        is_verified=user.is_verified,
        status=user.status,
        nickname=user.nickname,
        language_preference=user.language_preference,
        emergency_message_template=user.emergency_message_template,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        trusted_contacts=trusted_contacts_res,
        sos_alerts=sos_alerts_res,
        incident_reports=incident_reports_res,
        activity_log=activities
    )


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_operator_permission("users.suspend"))]
)
async def update_mobile_user_status(
    user_id: UUID,
    data: MobileUserStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update mobile user account status (e.g. suspend or restore user).
    """
    user_result = await db.execute(
        select(MobileUser).where(MobileUser.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mobile user not found"
        )

    # Update status
    user.status = data.status
    await db.flush()
    await db.refresh(user)

    # Load contacts eagerly for serialization
    from sqlalchemy.orm import selectinload
    user_with_contacts_result = await db.execute(
        select(MobileUser)
        .options(selectinload(MobileUser.trusted_contacts))
        .where(MobileUser.id == user_id)
    )
    user = user_with_contacts_result.scalar_one()
    return to_user_response(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_operator_permission("users.delete"))]
)
async def delete_mobile_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently delete a mobile user.
    """
    user_result = await db.execute(
        select(MobileUser).where(MobileUser.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mobile user not found"
        )

    await db.delete(user)
    await db.commit()
