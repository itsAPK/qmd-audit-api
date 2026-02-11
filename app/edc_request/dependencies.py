
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.edc_request.services import EdcRequestService
from app.core.database import get_session

async def get_edc_request_service(
    session: AsyncSession = Depends(get_session),
) -> EdcRequestService:
    return EdcRequestService(session=session)