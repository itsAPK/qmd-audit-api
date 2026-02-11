from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services import AuthService
from app.core.database import get_session

async def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    return AuthService(session=session)