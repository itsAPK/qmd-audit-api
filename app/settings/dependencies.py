from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.services import SettingsService
from app.core.database import get_session

async def get_settings_service(
    session: AsyncSession = Depends(get_session),
) -> SettingsService:
    return SettingsService(session=session)