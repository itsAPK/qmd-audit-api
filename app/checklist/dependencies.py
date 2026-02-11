from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.checklist.services import ChecklistService
from app.core.database import get_session

async def get_checklist_service(
    session: AsyncSession = Depends(get_session),
) -> ChecklistService:
    return ChecklistService(session=session)