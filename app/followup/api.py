from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.schemas import Response, ResponseStatus
from app.followup.models import CreateFollowupRequest, Followup, FollowupListResponse,FollowupResponse, UpdateFollowupRequest
from app.followup.services import FollowupService
from app.followup.dependencies import get_followup_service
from app.users.models import User
from app.core.security import authenticate

router = APIRouter()

@router.post("", response_model=Response[Followup])
async def create_followup(
    data: CreateFollowupRequest, followup_service: FollowupService = Depends(get_followup_service),
    user : User = Depends(authenticate),
):
    followup = await followup_service.create_followup(data, user.id)
    return Response(
        message="Followup created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=followup,
    )
    
@router.get("", response_model=Response[FollowupListResponse])
async def get_all_followups(
    filters : Optional[str] = None,
    sort: Optional[str] = None,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    followup_service: FollowupService = Depends(get_followup_service),
):
    followups = await followup_service.get_all_followups(filters, sort, page, page_size)
    return Response(
        message="Followups fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=followups,
    )
    
@router.get("/{followup_id}", response_model=Response[FollowupResponse])
async def get_followup(
    followup_id: UUID,
    followup_service: FollowupService = Depends(get_followup_service),
):
    followup = await followup_service.get_followup_by_id(followup_id)
    return Response(
        message="Followup fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=followup,
    )
    
@router.patch("/{followup_id}", response_model=Response[Followup])
async def update_followup(
    followup_id: UUID,
    data: UpdateFollowupRequest,
    followup_service: FollowupService = Depends(get_followup_service),
):
    followup = await followup_service.update_followup(followup_id, data)
    return Response(
        message="Followup updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=followup,
    )
    
    
@router.get("/export/all", response_model=Response[list[FollowupResponse]])
async def export_all_followups(
    filters : Optional[str] = None,
    sort: Optional[str] = None,
    followup_service: FollowupService = Depends(get_followup_service),
):
    followups = await followup_service.export_all_followups(filters, sort)
    return Response(
        message="Followups fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=followups,
    )