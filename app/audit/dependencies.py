from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.services import AuditService
from app.core.database import get_session

async def get_audit_service(
    session: AsyncSession = Depends(get_session),
) -> AuditService:
    return AuditService(session=session)