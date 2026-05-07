"""
Permission Enum System - Source of Truth

All system permissions are defined here as string constants.
Permissions are NOT stored in database; they are controlled by this enum only.
New permissions must be added here and roles can be assigned these permissions.
"""

from enum import Enum
from typing import List, Dict, Set


class PermissionEnum(str, Enum):
    """
    Enterprise RBAC Permission Enum

    All institutional operator permissions are defined here.
    Format: module.action
    """

    # ==================== SOS EMERGENCY ====================
    SOS_VIEW = "sos.view"
    SOS_CREATE = "sos.create"
    SOS_ASSIGN = "sos.assign"
    SOS_RESPOND = "sos.respond"
    SOS_ESCALATE = "sos.escalate"
    SOS_CLOSE = "sos.close"
    SOS_DELETE = "sos.delete"
    SOS_EXPORT = "sos.export"

    # ==================== CASES / INCIDENT REPORTS ====================
    CASES_VIEW = "cases.view"
    CASES_VIEW_ALL = "cases.view_all"
    CASES_CREATE = "cases.create"
    CASES_UPDATE = "cases.update"
    CASES_UPDATE_STATUS = "cases.update_status"
    CASES_ASSIGN = "cases.assign"
    CASES_RESOLVE = "cases.resolve"
    CASES_ESCALATE = "cases.escalate"
    CASES_DELETE = "cases.delete"
    CASES_EXPORT = "cases.export"
    CASES_MERGE = "cases.merge"

    # ==================== EVIDENCE MANAGEMENT ====================
    EVIDENCE_VIEW = "evidence.view"
    EVIDENCE_DOWNLOAD = "evidence.download"
    EVIDENCE_UPLOAD = "evidence.upload"
    EVIDENCE_DELETE = "evidence.delete"
    EVIDENCE_VERIFY = "evidence.verify"
    EVIDENCE_EXPORT = "evidence.export"
    EVIDENCE_CHAIN_OF_CUSTODY = "evidence.chain_of_custody"

    # ==================== USER MANAGEMENT ====================
    USERS_VIEW = "users.view"
    USERS_VIEW_ALL = "users.view_all"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_SUSPEND = "users.suspend"
    USERS_DELETE = "users.delete"
    USERS_EXPORT = "users.export"
    USERS_ASSIGN_ROLES = "users.assign_roles"
    USERS_MANAGE_PERMISSIONS = "users.manage_permissions"

    # ==================== OPERATOR USER MANAGEMENT ====================
    OPERATORS_VIEW = "operators.view"
    OPERATORS_CREATE = "operators.create"
    OPERATORS_UPDATE = "operators.update"
    OPERATORS_SUSPEND = "operators.suspend"
    OPERATORS_DELETE = "operators.delete"
    OPERATORS_ASSIGN_ROLES = "operators.assign_roles"
    OPERATORS_MANAGE_PERMISSIONS = "operators.manage_permissions"

    # ==================== ROLE MANAGEMENT ====================
    ROLES_VIEW = "roles.view"
    ROLES_CREATE = "roles.create"
    ROLES_UPDATE = "roles.update"
    ROLES_DELETE = "roles.delete"
    ROLES_ASSIGN_PERMISSIONS = "roles.assign_permissions"
    ROLES_MANAGE_SYSTEM = "roles.manage_system"

    # ==================== SUPPORT CENTERS ====================
    SUPPORT_CENTERS_VIEW = "support_centers.view"
    SUPPORT_CENTERS_CREATE = "support_centers.create"
    SUPPORT_CENTERS_UPDATE = "support_centers.update"
    SUPPORT_CENTERS_DELETE = "support_centers.delete"
    SUPPORT_CENTERS_MANAGE = "support_centers.manage"
    SUPPORT_CENTERS_VERIFY = "support_centers.verify"

    # ==================== MESSAGING ====================
    MESSAGES_VIEW = "messages.view"
    MESSAGES_VIEW_ALL = "messages.view_all"
    MESSAGES_SEND = "messages.send"
    MESSAGES_RESPOND = "messages.respond"
    MESSAGES_DELETE = "messages.delete"
    MESSAGES_EXPORT = "messages.export"
    CONVERSATIONS_VIEW = "conversations.view"
    CONVERSATIONS_MANAGE = "conversations.manage"

    # ==================== TRAINING MODULES ====================
    TRAINING_VIEW = "training.view"
    TRAINING_CREATE = "training.create"
    TRAINING_UPDATE = "training.update"
    TRAINING_DELETE = "training.delete"
    TRAINING_MANAGE = "training.manage"
    TRAINING_ENROLL_USERS = "training.enroll_users"
    TRAINING_VIEW_PROGRESS = "training.view_progress"

    # ==================== ANALYTICS & REPORTING ====================
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_VIEW_ALL = "analytics.view_all"
    ANALYTICS_EXPORT = "analytics.export"
    ANALYTICS_DASHBOARD = "analytics.dashboard"
    REPORTS_VIEW = "reports.view"
    REPORTS_CREATE = "reports.create"
    REPORTS_EXPORT = "reports.export"
    REPORTS_SCHEDULE = "reports.schedule"

    # ==================== AUDIT & COMPLIANCE ====================
    AUDIT_LOGS_VIEW = "audit_logs.view"
    AUDIT_LOGS_EXPORT = "audit_logs.export"
    AUDIT_LOGS_DELETE = "audit_logs.delete"
    COMPLIANCE_VIEW = "compliance.view"
    COMPLIANCE_EXPORT = "compliance.export"

    # ==================== SYSTEM ADMINISTRATION ====================
    SYSTEM_SETTINGS_VIEW = "system.settings_view"
    SYSTEM_SETTINGS_UPDATE = "system.settings_update"
    SYSTEM_MAINTENANCE = "system.maintenance"
    SYSTEM_BACKUP = "system.backup"
    SYSTEM_RESTORE = "system.restore"
    INTEGRATIONS_VIEW = "integrations.view"
    INTEGRATIONS_MANAGE = "integrations.manage"

    # ==================== REGIONAL MANAGEMENT ====================
    REGIONS_VIEW = "regions.view"
    REGIONS_MANAGE = "regions.manage"
    REGIONAL_ANALYTICS = "regional.analytics"
    REGIONAL_USERS_VIEW = "regional.users_view"
    REGIONAL_CASES_VIEW = "regional.cases_view"

    # ==================== ORGANIZATION MANAGEMENT (NGOs) ====================
    ORGS_VIEW = "orgs.view"
    ORGS_CREATE = "orgs.create"
    ORGS_UPDATE = "orgs.update"
    ORGS_DELETE = "orgs.delete"
    ORGS_MANAGE_STAFF = "orgs.manage_staff"
    ORGS_VIEW_ANALYTICS = "orgs.view_analytics"

    # ==================== NOTIFICATIONS ====================
    NOTIFICATIONS_VIEW = "notifications.view"
    NOTIFICATIONS_SEND = "notifications.send"
    NOTIFICATIONS_MANAGE_TEMPLATES = "notifications.manage_templates"
    BROADCAST_SEND = "broadcast.send"

    # ==================== SUPER ADMIN ====================
    SUPER_ADMIN_ACCESS = "super_admin.access"
    SUPER_ADMIN_IMPERSONATE = "super_admin.impersonate"
    SUPER_ADMIN_SYSTEM_CONFIG = "super_admin.system_config"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def all_permissions(cls) -> Set[str]:
        """Return all permission values as a set of strings."""
        return {p.value for p in cls}

    @classmethod
    def grouped_by_module(cls) -> Dict[str, List[str]]:
        """Return permissions grouped by module prefix."""
        groups: Dict[str, List[str]] = {}
        for p in cls:
            module = p.value.split(".")[0]
            if module not in groups:
                groups[module] = []
            groups[module].append(p.value)
        return groups

    @classmethod
    def validate_permission(cls, permission_code: str) -> bool:
        """Validate if a permission code is valid."""
        return permission_code in cls.all_permissions()

    @classmethod
    def from_string(cls, permission_code: str) -> "PermissionEnum":
        """Get PermissionEnum from string value."""
        for p in cls:
            if p.value == permission_code:
                return p
        raise ValueError(f"Invalid permission code: {permission_code}")


# Predefined Role Permission Mappings (for system roles)
SYSTEM_ROLE_PERMISSIONS = {
    "super_admin": PermissionEnum.all_permissions(),
    "police_officer": {
        PermissionEnum.SOS_VIEW.value,
        PermissionEnum.SOS_RESPOND.value,
        PermissionEnum.SOS_ASSIGN.value,
        PermissionEnum.CASES_VIEW.value,
        PermissionEnum.CASES_CREATE.value,
        PermissionEnum.CASES_UPDATE.value,
        PermissionEnum.EVIDENCE_VIEW.value,
        PermissionEnum.EVIDENCE_DOWNLOAD.value,
        PermissionEnum.MESSAGES_VIEW.value,
        PermissionEnum.MESSAGES_RESPOND.value,
        PermissionEnum.ANALYTICS_VIEW.value,
        PermissionEnum.AUDIT_LOGS_VIEW.value,
        PermissionEnum.SUPPORT_CENTERS_VIEW.value,
    },
    "legal_officer": {
        PermissionEnum.CASES_VIEW_ALL.value,
        PermissionEnum.CASES_UPDATE.value,
        PermissionEnum.CASES_RESOLVE.value,
        PermissionEnum.CASES_ESCALATE.value,
        PermissionEnum.EVIDENCE_VIEW.value,
        PermissionEnum.EVIDENCE_DOWNLOAD.value,
        PermissionEnum.EVIDENCE_VERIFY.value,
        PermissionEnum.EVIDENCE_CHAIN_OF_CUSTODY.value,
        PermissionEnum.USERS_VIEW.value,
        PermissionEnum.MESSAGES_VIEW.value,
        PermissionEnum.ANALYTICS_VIEW.value,
        PermissionEnum.REPORTS_VIEW.value,
        PermissionEnum.COMPLIANCE_VIEW.value,
    },
    "counselor": {
        PermissionEnum.SOS_VIEW.value,
        PermissionEnum.SOS_RESPOND.value,
        PermissionEnum.CASES_VIEW.value,
        PermissionEnum.CASES_UPDATE_STATUS.value,
        PermissionEnum.MESSAGES_VIEW.value,
        PermissionEnum.MESSAGES_RESPOND.value,
        PermissionEnum.CONVERSATIONS_VIEW.value,
        PermissionEnum.TRAINING_VIEW.value,
        PermissionEnum.SUPPORT_CENTERS_VIEW.value,
        PermissionEnum.USERS_VIEW.value,
    },
    "help_center_staff": {
        PermissionEnum.SOS_VIEW.value,
        PermissionEnum.SOS_RESPOND.value,
        PermissionEnum.SOS_ASSIGN.value,
        PermissionEnum.CASES_VIEW.value,
        PermissionEnum.CASES_CREATE.value,
        PermissionEnum.CASES_UPDATE_STATUS.value,
        PermissionEnum.MESSAGES_VIEW.value,
        PermissionEnum.MESSAGES_RESPOND.value,
        PermissionEnum.SUPPORT_CENTERS_VIEW.value,
        PermissionEnum.SUPPORT_CENTERS_UPDATE.value,
    },
    "ngo_manager": {
        PermissionEnum.ORGS_VIEW.value,
        PermissionEnum.ORGS_UPDATE.value,
        PermissionEnum.ORGS_MANAGE_STAFF.value,
        PermissionEnum.ORGS_VIEW_ANALYTICS.value,
        PermissionEnum.CASES_VIEW.value,
        PermissionEnum.CASES_CREATE.value,
        PermissionEnum.MESSAGES_VIEW.value,
        PermissionEnum.MESSAGES_RESPOND.value,
        PermissionEnum.ANALYTICS_VIEW.value,
        PermissionEnum.SUPPORT_CENTERS_VIEW.value,
        PermissionEnum.TRAINING_VIEW.value,
    },
    "regional_manager": {
        PermissionEnum.REGIONS_VIEW.value,
        PermissionEnum.REGIONS_MANAGE.value,
        PermissionEnum.REGIONAL_ANALYTICS.value,
        PermissionEnum.REGIONAL_USERS_VIEW.value,
        PermissionEnum.REGIONAL_CASES_VIEW.value,
        PermissionEnum.CASES_VIEW_ALL.value,
        PermissionEnum.CASES_ASSIGN.value,
        PermissionEnum.OPERATORS_VIEW.value,
        PermissionEnum.SUPPORT_CENTERS_MANAGE.value,
        PermissionEnum.ANALYTICS_VIEW_ALL.value,
        PermissionEnum.REPORTS_VIEW.value,
        PermissionEnum.REPORTS_CREATE.value,
    },
    "auditor": {
        PermissionEnum.AUDIT_LOGS_VIEW.value,
        PermissionEnum.AUDIT_LOGS_EXPORT.value,
        PermissionEnum.COMPLIANCE_VIEW.value,
        PermissionEnum.COMPLIANCE_EXPORT.value,
        PermissionEnum.ANALYTICS_VIEW.value,
        PermissionEnum.REPORTS_VIEW.value,
        PermissionEnum.CASES_VIEW_ALL.value,
        PermissionEnum.EVIDENCE_VIEW.value,
        PermissionEnum.USERS_VIEW_ALL.value,
    },
}


def get_system_role_permissions(role_name: str) -> Set[str]:
    """Get predefined permissions for system roles."""
    return set(SYSTEM_ROLE_PERMISSIONS.get(role_name.lower(), set()))


def get_all_system_roles() -> List[str]:
    """Get list of all system role names."""
    return list(SYSTEM_ROLE_PERMISSIONS.keys())
