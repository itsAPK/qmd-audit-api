from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.audit.dependencies import get_audit_service
from app.audit.services import AuditService
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.schemas import Response, ResponseStatus
from app.audit.models import (
    Audit,
    AuditIdResponse,
    AuditRequest,
    AuditResponse,
    AuditSchedule,
    AuditStandard,
    AuditType,
    AuditSettingsRequest,
    AuditTypeRequest,
    AuditListResponse,
    AuditUpdateRequest,
)
from app.core.security import authenticate
from app.users.models import User

router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[Audit],
)
async def create_audit(
    data: AuditRequest,
    audit_service: AuditService = Depends(get_audit_service),
    user: User = Depends(authenticate),
):
    audit = await audit_service.create_audit(data, user.id)
    return Response(
        message="Audit created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditListResponse],
)
async def get_all_audits(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    audit_service: AuditService = Depends(get_audit_service),
     from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
):
    audits = await audit_service.get_all_audits(
        filters=filters,
        sort=sort,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
    )
    return Response(
        message="Audits fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audits,
    )


@router.get(
    "/export/all",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[AuditResponse]],
)
async def export_all_audits(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    audit_service: AuditService = Depends(get_audit_service),
     from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
):
    audits = await audit_service.export_all_audits(
        filters=filters,
        sort=sort,
        from_date=from_date,
        to_date=to_date,
    )
    return Response(
        message="Audits fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audits,
    )


@router.get(
    "/{audit_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[Audit],
)
async def get_audit_by_id(
    audit_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit = await audit_service.get_audit_by_id(audit_id)
    return Response(
        message="Audit fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit,
    )


@router.get(
    "/all/ids",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[AuditIdResponse]],
)
async def get_audit_ids(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    audit_service: AuditService = Depends(get_audit_service),
     from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
):
    audit_ids = await audit_service.get_all_audit_ids(
        filters=filters,
        sort=sort,
        from_date=from_date,
        to_date=to_date,
    )
    return Response(
        message="Audit ids fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_ids,
    )

@router.patch(
    "/{audit_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[Audit],
)
async def update_audit(
    audit_id: UUID,
    data: AuditUpdateRequest,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit = await audit_service.update_audit(audit_id, data)
    return Response(
        message="Audit updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit,
    )



@router.delete(
    "/{audit_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[bool],
)
async def delete_audit(
    audit_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit = await audit_service.delete_audit(audit_id)
    return Response(
        message="Audit deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit,
    )


@router.post(
    "/config/audit-schedules",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[AuditSchedule],
)
async def create_audit_schedule(
    data: AuditSettingsRequest,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_schedule = await audit_service.create_audit_schedule(data)
    return Response(
        message="Audit schedule created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_schedule,
    )


@router.get(
    "/config/audit-schedules",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[AuditSchedule]],
)
async def get_all_audit_schedules(
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_schedules = await audit_service.get_all_audit_schedules()
    return Response(
        message="Audit schedules fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_schedules,
    )


@router.get(
    "/config/audit-schedules/{audit_schedule_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditSchedule],
)
async def get_audit_schedule_by_id(
    audit_schedule_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_schedule = await audit_service.get_audit_schedule_by_id(audit_schedule_id)
    return Response(
        message="Audit schedule fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_schedule,
    )


@router.patch(
    "/config/audit-schedules/{audit_schedule_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditSchedule],
)
async def update_audit_schedule(
    audit_schedule_id: UUID,
    data: AuditSettingsRequest,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_schedule = await audit_service.update_audit_schedule(audit_schedule_id, data)
    return Response(
        message="Audit schedule updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_schedule,
    )


@router.delete(
    "/config/audit-schedules/{audit_schedule_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[bool],
)
async def delete_audit_schedule(
    audit_schedule_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_schedule = await audit_service.delete_audit_schedule(audit_schedule_id)
    return Response(
        message="Audit schedule deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.post(
    "/config/audit-types",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[AuditType],
)
async def create_audit_type(
    data: AuditTypeRequest,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_type = await audit_service.create_audit_type(data)
    return Response(
        message="Audit type created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_type,
    )


@router.get(
    "/config/audit-types",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[AuditType]],
)
async def get_all_audit_types(
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_types = await audit_service.get_all_audit_types()
    return Response(
        message="Audit types fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_types,
    )


@router.get(
    "/config/audit-types/{audit_type_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditType],
)
async def get_audit_type_by_id(
    audit_type_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_type = await audit_service.get_audit_type_by_id(audit_type_id)
    return Response(
        message="Audit type fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_type,
    )


@router.patch(
    "/config/audit-types/{audit_type_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditType],
)
async def update_audit_type(
    audit_type_id: UUID,
    data: AuditTypeRequest,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_type = await audit_service.update_audit_type(audit_type_id, data)
    return Response(
        message="Audit type updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_type,
    )


@router.delete(
    "/config/audit-types/{audit_type_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[bool],
)
async def delete_audit_type(
    audit_type_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_type = await audit_service.delete_audit_type(audit_type_id)
    return Response(
        message="Audit type deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.post(
    "/config/audit-standards",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[AuditStandard],
)
async def create_audit_standard(
    data: AuditSettingsRequest,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_standard = await audit_service.create_audit_standard(data)
    return Response(
        message="Audit standard created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_standard,
    )


@router.get(
    "/config/audit-standards",
    status_code=status.HTTP_200_OK,
    response_model=Response[list[AuditStandard]],
)
async def get_all_audit_standards(
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_standards = await audit_service.get_all_audit_standards()
    return Response(
        message="Audit standards fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_standards,
    )


@router.get(
    "/config/audit-standards/{audit_standard_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditStandard],
)
async def get_audit_standard_by_id(
    audit_standard_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_standard = await audit_service.get_audit_standard_by_id(audit_standard_id)
    return Response(
        message="Audit standard fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_standard,
    )


@router.patch(
    "/config/audit-standards/{audit_standard_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AuditStandard],
)
async def update_audit_standard(
    audit_standard_id: UUID,
    data: AuditSettingsRequest,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_standard = await audit_service.update_audit_standard(audit_standard_id, data)
    return Response(
        message="Audit standard updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=audit_standard,
    )


@router.delete(
    "/config/audit-standards/{audit_standard_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[bool],
)
async def delete_audit_standard(
    audit_standard_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    audit_standard = await audit_service.delete_audit_standard(audit_standard_id)
    return Response(
        message="Audit standard deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.get("/{audit_id}/ncr-status-report", response_model=Response[dict])
async def get_ncr_status_report(
    audit_id: UUID,
    audit_service: AuditService = Depends(get_audit_service),
):
    ncr_status_report = await audit_service.get_ncr_status_report(audit_id)
    return Response(
        message="NCR status report fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr_status_report,
    )
    
