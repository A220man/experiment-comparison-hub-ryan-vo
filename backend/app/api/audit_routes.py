import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_ADMIN, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.entities import AuditLog
from backend.app.models.schemas import AuditLogListResponse, AuditLogResponse
router = APIRouter(prefix='/audit-logs', tags=['Audit Logs'])

@router.get('', response_model=AuditLogListResponse)
def list_audit_logs(page: int=Query(default=1, ge=1), page_size: int=Query(default=50, ge=1, le=100), db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ADMIN))):
    query = db.query(AuditLog)
    total = query.count()
    items = query.order_by(desc(AuditLog.timestamp)).offset((page - 1) * page_size).limit(page_size).all()
    pages = math.ceil(total / page_size) if total > 0 else 1
    return AuditLogListResponse(items=[AuditLogResponse.model_validate(log) for log in items], total=total, page=page, page_size=page_size, pages=pages)
