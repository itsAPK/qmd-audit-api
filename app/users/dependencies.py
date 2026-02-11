from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.services import UserService
from app.core.database import get_session

async def get_user_service(
    session: AsyncSession = Depends(get_session),
) -> UserService:
    return UserService(session=session)