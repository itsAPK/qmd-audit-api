from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from app.audit_info.dependencies import get_audit_info_service
from app.audit_info.services import AuditInfoService
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.schemas import Response, ResponseStatus
from app.audit_info.models import (
    AuditInfo,
    AuditInfoListResponse,
    AuditInfoRequest,
    AuditInfoResponse,
    AuditInfoUpdateRequest,
    AuditTeam,
    AuditTeamRequest,
    AuditTeamResponse,
)
from app.core.security import authenticate
from app.users.models import User


router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[AuditInfo],
)
async def create_audit_info(
    data: AuditInfoRequest,
    background_tasks: BackgroundTasks,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),

):
    audit_info = await audit_info_service.create_audit_info(data, background_tasks)
    return Response(
        message="Audit info created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_info,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditInfoListResponse],
)
async def get_all_audit_info(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),
):
    audit_infos = await audit_info_service.get_all_audit_info(
        filters=filters,
        sort=sort,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
    )
    return Response(
        message="Audit info fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_infos,
    )


@router.get(
    "/{audit_info_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditInfoResponse],
)
async def get_audit_info_by_id(
    audit_info_id: UUID,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),
):
    audit_info = await audit_info_service.get_audit_info_by_id(audit_info_id)
    return Response(
        message="Audit info fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_info,
    )


@router.patch(
    "/{audit_info_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditInfo],
)
async def update_audit_info(
    audit_info_id: UUID,
    data: AuditInfoUpdateRequest,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),
):
    audit_info = await audit_info_service.update_audit_info(audit_info_id, data)
    return Response(
        message="Audit info updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_info,
    )


@router.delete(
    "/{audit_info_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[bool],
)
async def delete_audit_info(
    audit_info_id: UUID,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),
):
    audit_info = await audit_info_service.delete_audit_info(audit_info_id)
    return Response(
        message="Audit info deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_info,
    )


@router.post(
    "/{audit_info_id}/audit-team",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[AuditTeam],
)
async def create_audit_team(
    data: AuditTeamRequest,
    audit_info_id: UUID,
    background_tasks: BackgroundTasks,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),
):
    audit_team = await audit_info_service.create_audit_team(data, audit_info_id, background_tasks)
    return Response(
        message="Audit team created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_team,
    )


@router.delete(
    "/{audit_info_id}/audit-team/{audit_team_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[bool],
)
async def remove_audit_team(
    audit_info_id: UUID,
    audit_team_id: UUID,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),
):
    audit_team = await audit_info_service.remove_audit_team(
        audit_info_id, audit_team_id
    )
    return Response(
        message="Audit team deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.get(
    "/export/all",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[AuditInfoResponse]],
)
async def export_all_audit_info(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),
):
    audit_infos = await audit_info_service.export_all_audit_info(
        filters=filters, sort=sort, from_date=from_date, to_date=to_date
    )
    return Response(
        message="Audit info fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_infos,
    )


@router.get(
    "/audit/{audit_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[AuditInfoResponse]],
)
async def get_audit_info_by_audit_id(
    audit_id: UUID,
    audit_info_service: AuditInfoService = Depends(get_audit_info_service),
):
    audit_infos = await audit_info_service.get_audit_info_by_audit_id(audit_id)
    return Response(
        message="Audit info fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_infos,
    )
