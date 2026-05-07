from sqlmodel import SQLModel

from app.models.user import User, AnonymousSession, TrustedContact, OTPCode
from app.models.sos import SOSAlert, LocationPing
from app.models.reporting import IncidentReport, EvidenceFile
from app.models.messaging import Conversation, ConversationParticipant, Message
from app.models.support import SupportCenter
from app.models.training import TrainingCategory, TrainingLesson

# Operator RBAC models (separate module)
from app.operator_models.operator import (
    OperatorUser,
    Role,
    RolePermissionLink,
    UserRoleLink,
    UserPermissionOverride,
)

__all__ = [
    "SQLModel",
    # Survivor/Mobile models
    "User",
    "AnonymousSession",
    "TrustedContact",
    "OTPCode",
    "SOSAlert",
    "LocationPing",
    "IncidentReport",
    "EvidenceFile",
    "Conversation",
    "ConversationParticipant",
    "Message",
    "SupportCenter",
    "TrainingCategory",
    "TrainingLesson",
    # Operator RBAC models
    "OperatorUser",
    "Role",
    "RolePermissionLink",
    "UserRoleLink",
    "UserPermissionOverride",
]
