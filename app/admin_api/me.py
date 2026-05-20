"""
Current Operator Session API Routes

- GET /api/v1/operator/me/permissions - Get my effective permissions
- GET /api/v1/operator/me/sidebar - Get sidebar menu based on permissions
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import get_current_operator
from app.operator_models.operator import OperatorUser
from app.operator_schemas.permission import (
    EffectivePermissionsResponse,
    SidebarMenuResponse,
    MenuItem,
)
from app.rbac.services.permission_resolver_service import permission_resolver
from app.schemas.support import (
    SupportCenterResponse,
    SupportCenterCreate,
    SupportCenterUpdate,
    to_support_center_response
)
from app.repositories.support import support_center_repo
from app.models.support import SupportCenter
from app.operator_repositories.operator_user import operator_user_repo

router = APIRouter()


def _get_menu_for_permission(perm: str) -> List[MenuItem]:
    """Get menu items associated with a permission."""
    menu_map = {
        # SOS
        "sos.view": [MenuItem(id="sos", label="SOS Alerts", icon="bell", route="/sos")],
        "sos.respond": [MenuItem(id="sos-respond", label="Respond to SOS", icon="phone", route="/sos/respond")],
        
        # Cases
        "cases.view": [MenuItem(id="cases", label="Cases", icon="folder", route="/cases")],
        "cases.view_all": [MenuItem(id="cases-all", label="All Cases", icon="folders", route="/cases/all")],
        
        # Evidence
        "evidence.view": [MenuItem(id="evidence", label="Evidence", icon="file-text", route="/evidence")],
        
        # Users
        "users.view": [MenuItem(id="users", label="Survivors", icon="users", route="/users")],
        "users.view_all": [MenuItem(id="users-all", label="All Survivors", icon="users", route="/users/all")],
        
        # Operators
        "operators.view": [MenuItem(id="operators", label="Staff", icon="user-check", route="/operators")],
        
        # Roles
        "roles.view": [MenuItem(id="roles", label="Roles", icon="shield", route="/roles")],
        
        # Support Centers
        "support_centers.view": [MenuItem(id="centers", label="Support Centers", icon="map-pin", route="/centers")],
        "support_centers.manage": [MenuItem(id="centers-manage", label="Manage Centers", icon="settings", route="/centers/manage")],
        
        # Messages
        "messages.view": [MenuItem(id="messages", label="Messages", icon="message-circle", route="/messages")],
        "conversations.view": [MenuItem(id="conversations", label="Conversations", icon="message-square", route="/conversations")],
        
        # Training
        "training.view": [MenuItem(id="training", label="Training", icon="book-open", route="/training")],
        "training.manage": [MenuItem(id="training-manage", label="Manage Training", icon="edit", route="/training/manage")],
        
        # Analytics
        "analytics.view": [MenuItem(id="analytics", label="Analytics", icon="bar-chart", route="/analytics")],
        "analytics.dashboard": [MenuItem(id="dashboard", label="Dashboard", icon="layout", route="/dashboard")],
        
        # Reports
        "reports.view": [MenuItem(id="reports", label="Reports", icon="file", route="/reports")],
        
        # Audit
        "audit_logs.view": [MenuItem(id="audit", label="Audit Logs", icon="clipboard", route="/audit")],
        
        # System
        "system.settings_view": [MenuItem(id="settings", label="Settings", icon="settings", route="/settings")],
    }
    
    return menu_map.get(perm, [])


def _build_sidebar(effective_perms: List[str]) -> List[MenuItem]:
    """Build sidebar menu from effective permissions."""
    # Collect all menu items user has access to
    menu_items: dict = {}
    for perm in effective_perms:
        for item in _get_menu_for_permission(perm):
            menu_items[item.id] = item
    
    # Define menu structure with hierarchy
    sidebar: List[MenuItem] = []
    
    # Dashboard (always available to logged-in operators)
    sidebar.append(MenuItem(
        id="dashboard",
        label="Dashboard",
        icon="layout",
        route="/dashboard"
    ))
    
    # SOS Section
    if any(p in effective_perms for p in ["sos.view", "sos.respond"]):
        sos_children = []
        if "sos.view" in effective_perms:
            sos_children.append(MenuItem(id="sos-list", label="Active Alerts", route="/sos"))
        if "sos.respond" in effective_perms:
            sos_children.append(MenuItem(id="sos-respond", label="Respond", route="/sos/respond"))
        
        sidebar.append(MenuItem(
            id="sos",
            label="SOS Emergency",
            icon="bell",
            children=sos_children if len(sos_children) > 1 else None,
            route="/sos" if len(sos_children) == 1 else None
        ))
    
    # Cases Section
    if any(p in effective_perms for p in ["cases.view", "cases.view_all", "cases.create"]):
        case_children = []
        if "cases.view" in effective_perms or "cases.view_all" in effective_perms:
            case_children.append(MenuItem(id="cases-list", label="All Cases", route="/cases"))
        if "cases.create" in effective_perms:
            case_children.append(MenuItem(id="cases-create", label="New Case", route="/cases/new"))
        
        sidebar.append(MenuItem(
            id="cases",
            label="Cases",
            icon="folder",
            children=case_children if len(case_children) > 1 else None,
            route="/cases" if len(case_children) == 1 else None
        ))
    
    # Evidence
    if "evidence.view" in effective_perms:
        sidebar.append(MenuItem(
            id="evidence",
            label="Evidence",
            icon="file-text",
            route="/evidence"
        ))
    
    # Users/Survivors
    if any(p in effective_perms for p in ["users.view", "users.view_all"]):
        sidebar.append(MenuItem(
            id="users",
            label="Survivors",
            icon="users",
            route="/users"
        ))
    
    # Messages
    if any(p in effective_perms for p in ["messages.view", "conversations.view"]):
        sidebar.append(MenuItem(
            id="messages",
            label="Messages",
            icon="message-circle",
            route="/messages"
        ))
    
    # Support Centers
    if any(p in effective_perms for p in ["support_centers.view", "support_centers.manage"]):
        sidebar.append(MenuItem(
            id="centers",
            label="Support Centers",
            icon="map-pin",
            route="/centers"
        ))
    
    # Training
    if any(p in effective_perms for p in ["training.view", "training.manage"]):
        sidebar.append(MenuItem(
            id="training",
            label="Training",
            icon="book-open",
            route="/training"
        ))
    
    # Analytics & Reports
    if any(p in effective_perms for p in ["analytics.view", "analytics.dashboard", "reports.view"]):
        analytics_children = []
        if "analytics.dashboard" in effective_perms:
            analytics_children.append(MenuItem(id="analytics-dashboard", label="Dashboard", route="/analytics"))
        if "reports.view" in effective_perms:
            analytics_children.append(MenuItem(id="reports", label="Reports", route="/reports"))
        
        sidebar.append(MenuItem(
            id="analytics",
            label="Analytics",
            icon="bar-chart",
            children=analytics_children if len(analytics_children) > 1 else None,
            route="/analytics" if len(analytics_children) == 1 else None
        ))
    
    # Staff Management (for operators who can view operators)
    if "operators.view" in effective_perms:
        staff_children = []
        if "operators.view" in effective_perms:
            staff_children.append(MenuItem(id="operators-list", label="Staff Members", route="/operators"))
        if "roles.view" in effective_perms:
            staff_children.append(MenuItem(id="roles", label="Roles", route="/roles"))
        
        sidebar.append(MenuItem(
            id="staff",
            label="Staff Management",
            icon="user-check",
            children=staff_children if len(staff_children) > 1 else None,
            route="/operators" if len(staff_children) == 1 else None
        ))
    
    # Audit (for auditors)
    if "audit_logs.view" in effective_perms:
        sidebar.append(MenuItem(
            id="audit",
            label="Audit Logs",
            icon="clipboard",
            route="/audit"
        ))
    
    # Settings (for system settings)
    if "system.settings_view" in effective_perms or "super_admin.access" in effective_perms:
        sidebar.append(MenuItem(
            id="settings",
            label="Settings",
            icon="settings",
            route="/settings"
        ))
    
    return sidebar


@router.get(
    "/permissions",
    response_model=EffectivePermissionsResponse,
    status_code=status.HTTP_200_OK
)
async def get_my_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Get current operator's effective permissions breakdown."""
    breakdown = await permission_resolver.get_permission_breakdown(db, current_user.id)
    
    return EffectivePermissionsResponse(
        permissions=breakdown["permissions"],
        is_super_admin=breakdown["is_super_admin"],
        role_derived=breakdown["role_derived"],
        direct_grants=breakdown["direct_grants"],
        direct_denies=breakdown["direct_denies"]
    )


@router.get(
    "/sidebar",
    response_model=SidebarMenuResponse,
    status_code=status.HTTP_200_OK
)
async def get_my_sidebar(
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Get sidebar menu based on current operator's permissions."""
    effective_perms = await permission_resolver.get_effective_permissions(db, current_user.id)
    sidebar = _build_sidebar(list(effective_perms))
    
    return SidebarMenuResponse(
        items=sidebar,
        user_info={
            "id": str(current_user.id),
            "name": current_user.full_name,
            "email": current_user.email,
            "is_super_admin": str(current_user.is_super_admin)
        }
    )


@router.get(
    "/support-center",
    response_model=SupportCenterResponse,
    status_code=status.HTTP_200_OK
)
async def get_my_support_center(
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Get the support center linked to the current operator."""
    center = await support_center_repo.get_by_operator_id(db, current_user.id)
    if not center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No support center linked to this operator"
        )
    return to_support_center_response(center)


@router.post(
    "/support-center",
    response_model=SupportCenterResponse,
    status_code=status.HTTP_200_OK
)
async def setup_my_support_center(
    data: SupportCenterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: OperatorUser = Depends(get_current_operator)
):
    """Create or update the support center for the current operator."""
    existing_center = await support_center_repo.get_by_operator_id(db, current_user.id)
    
    if existing_center:
        # Update existing
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(existing_center, key, value)
        center = existing_center
    else:
        # Create new
        center = SupportCenter(**data.model_dump())
        center.operator_id = current_user.id
        db.add(center)
    
    # Mark setup as completed
    if not current_user.setup_completed:
        current_user.setup_completed = True
        # We need to update via repo to ensure it persists if session flush happens
        await operator_user_repo.update(db, db_obj=current_user, obj_in={"setup_completed": True})

    await db.commit()
    await db.refresh(center)
    
    return to_support_center_response(center)
