from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ncr.services import NCRService
from app.core.database import get_session

async def get_ncr_service(
    session: AsyncSession = Depends(get_session),
) -> NCRService:
    return NCRService(session=session)