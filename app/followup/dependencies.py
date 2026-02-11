from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.followup.services import FollowupService
from app.core.database import get_session

async def get_followup_service(
    session: AsyncSession = Depends(get_session),
) -> FollowupService:
    return FollowupService(session=session)