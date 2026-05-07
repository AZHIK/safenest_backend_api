"""Operator Authentication Module

Separate JWT authentication system for institutional operators.
Do NOT mix with survivor mobile app authentication.
"""

from app.operator_auth.dependencies import (
    get_current_operator,
    require_operator_permission,
    require_any_operator_permission,
    require_all_operator_permissions,
    get_optional_operator,
    require_operator_super_admin,  # Added export
)

__all__ = [
    "get_current_operator",
    "require_operator_permission",
    "require_any_operator_permission",
    "require_all_operator_permissions",
    "get_optional_operator",
    "require_operator_super_admin",  # Added export
]
