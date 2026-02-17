from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.suggestions.services import SuggestionService
from app.core.database import get_session

async def get_suggestion_service(
    session: AsyncSession = Depends(get_session),
) -> SuggestionService:
    return SuggestionService(session=session)