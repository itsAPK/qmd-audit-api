from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.services import DashboardService
from app.core.database import get_session

async def get_dashboard_service(
    session: AsyncSession = Depends(get_session),
) -> DashboardService:
    return DashboardService(session=session)