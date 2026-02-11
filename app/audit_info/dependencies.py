from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_info.services import AuditInfoService
from app.core.database import get_session

async def get_audit_info_service(
    session: AsyncSession = Depends(get_session),
) -> AuditInfoService:
    return AuditInfoService(session=session)