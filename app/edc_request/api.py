from typing import Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.schemas import Response, ResponseStatus
from app.edc_request.models import (
    CreateEdcRequestRequest,
    EdcRequest,
    EdcRequestListResponse,
    EdcRequestResponse,
    UpdateEDCRequestRequest,
)
from app.edc_request.services import EdcRequestService
from app.edc_request.dependencies import get_edc_request_service
from app.users.models import User
from app.core.security import authenticate

router = APIRouter()


@router.post("", response_model=Response[EdcRequest])
async def create_edc_request(
    data: CreateEdcRequestRequest,
background_tasks: BackgroundTasks,
    edc_request_service: EdcRequestService = Depends(get_edc_request_service),
    user: User = Depends(authenticate),
    
):
    edc_request = await edc_request_service.create_edc_request(data, user.id, background_tasks)
    return Response(
        message="Edc request created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=edc_request,
    )


@router.get("", response_model=Response[EdcRequestListResponse])
async def get_all_edc_requests(
    filters: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    edc_request_service: EdcRequestService = Depends(get_edc_request_service),
):
    edc_requests = await edc_request_service.get_all_edc_requests(
        filters, sort, page, page_size, from_date, to_date
    )
    return Response(
        message="Edc requests fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=edc_requests,
    )


@router.get("/{edc_request_id}", response_model=Response[EdcRequestResponse])
async def get_edc_request(
    edc_request_id: UUID,
    edc_request_service: EdcRequestService = Depends(get_edc_request_service),
):
    edc_request = await edc_request_service.get_edc_request_by_id(edc_request_id)
    return Response(
        message="Edc request fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=edc_request,
    )


@router.patch("/{edc_request_id}", response_model=Response[EdcRequest])
async def update_edc_request(
    edc_request_id: UUID,
    background_tasks: BackgroundTasks,
    data: UpdateEDCRequestRequest,
    edc_request_service: EdcRequestService = Depends(get_edc_request_service),
):
    edc_request = await edc_request_service.update_edc_request(edc_request_id, data, background_tasks)
    return Response(
        message="Edc request updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=edc_request,
    )


@router.get("/export/all", response_model=Response[EdcRequestResponse])
async def export_edc_requests(
    filters: Optional[str] = None,
    sort: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    edc_request_service: EdcRequestService = Depends(get_edc_request_service),
):
    edc_requests = await edc_request_service.export_edc_requests(
        filters, sort, from_date, to_date
    )
    return Response(
        message="Edc requests exported successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=edc_requests,
    )