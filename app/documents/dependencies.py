from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.services import DocumentsService
from app.core.database import get_session

async def get_document_service(
    session: AsyncSession = Depends(get_session),
) -> DocumentsService:
    return DocumentsService(session=session)