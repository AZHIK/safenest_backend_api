from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.operator_auth import require_operator_permission
from app.models.sos import SOSAlert, SOSStatus
from app.models.reporting import IncidentReport
from app.operator_models.operator import OperatorUser

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_operator=Depends(require_operator_permission("analytics.dashboard"))
):
    """Get aggregated statistics for the command center dashboard."""
    
    # 1. Active SOS Alerts
    active_sos_query = select(func.count(SOSAlert.id)).where(
        SOSAlert.status.in_([SOSStatus.ACTIVE, SOSStatus.ASSIGNED, SOSStatus.ESCALATED])
    )
    active_sos_count = (await db.execute(active_sos_query)).scalar() or 0
    
    # 2. Pending Reports (status is 'new' or 'under_review')
    pending_reports_query = select(func.count(IncidentReport.id)).where(
        IncidentReport.status.in_(["new", "under_review"])
    )
    pending_reports_count = (await db.execute(pending_reports_query)).scalar() or 0
    
    # 3. Responders Online (active operator users)
    responders_query = select(func.count(OperatorUser.id)).where(
        OperatorUser.is_active == True
    )
    responders_count = (await db.execute(responders_query)).scalar() or 0
    
    # 4. Average Response Time (for recently assigned alerts in the last 7 days)
    # response_time = assigned_at - created_at
    since = datetime.now(timezone.utc) - timedelta(days=7)
    avg_response_query = select(
        func.avg(
            func.extract('epoch', SOSAlert.assigned_at) - 
            func.extract('epoch', SOSAlert.created_at)
        )
    ).where(
        SOSAlert.assigned_at != None,
        SOSAlert.created_at >= since
    )
    avg_response_seconds = (await db.execute(avg_response_query)).scalar() or 0
    avg_response_minutes = round(avg_response_seconds / 60, 1) if avg_response_seconds else 0
    
    return {
        "active_sos_alerts": active_sos_count,
        "pending_reports": pending_reports_count,
        "responders_online": responders_count,
        "average_response_time": avg_response_minutes,
        "timestamp": datetime.now(timezone.utc)
    }
