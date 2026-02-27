
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends,BackgroundTasks

from app.core.schemas import Response,ResponseStatus
from app.checklist.models import FranchiseAuditChecklist, FranchiseAuditChecklistListResponse, FranchiseAuditChecklistRequest, FranchiseAuditChecklistResponse, FranchiseAuditChecklistUpdate, FranchiseAuditObservation, FranchiseAuditObservationRequest, FranchiseAuditObservationUpdate, InternalAuditObservationChecklist, InternalAuditObservationChecklistItem, InternalAuditObservationChecklistItemRequest, InternalAuditObservationChecklistListResponse, InternalAuditObservationChecklistRequest, InternalAuditObservationChecklistResponse, InternalAuditObservationChecklistUpdate, InternalAuditorsChecklistItem, InternalAuditorsChecklistItemRequest, InternalAuditorsChecklistRequested,InternalAuditorsChecklist, InternalAuditorsChecklistResponse, InternalAuditorsChecklistUpdate, InternalAuditorsChecklistListResponse
from app.checklist.services import ChecklistService
from app.checklist.dependencies import get_checklist_service
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.security import authenticate
from app.users.models import User

router = APIRouter()


@router.post("/internal_auditors", response_model=Response[InternalAuditorsChecklist])
async def create_internal_auditors_checklist(
    data: InternalAuditorsChecklistRequested,
    background_tasks : BackgroundTasks,
    checklist_service: ChecklistService = Depends(get_checklist_service),
    user : User = Depends(authenticate),
):
    res = await checklist_service.create_internal_auditors_checklist(
        data=data, background_tasks=background_tasks,user_id=user.id
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklist created successfully",
        data=res,
        status = ResponseStatus.CREATED
    )
    
    
@router.patch("/internal_auditors/{checklist_id}", response_model=Response[InternalAuditorsChecklist])
async def update_internal_auditors_checklist(
    checklist_id: UUID,
    data: InternalAuditorsChecklistUpdate,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.update_internal_auditors_checklist(
        item_id=checklist_id,
        data=data,
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item updated successfully",
        data=res,
        status = ResponseStatus.UPDATED
    )
    
@router.delete("/internal_auditors/{checklist_id}", response_model=Response[InternalAuditorsChecklist])
async def delete_internal_auditors_checklist(
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.delete_internal_auditors_checklist(checklist_id=checklist_id)
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item deleted successfully",
        data=res,
        status = ResponseStatus.DELETED
    )
    
@router.get("/internal_auditors/{checklist_id}", response_model=Response[InternalAuditorsChecklistResponse])
async def get_internal_auditors_checklist_by_id(
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.get_internal_auditors_checklist_by_id(checklist_id=checklist_id)
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item retrieved successfully",
        data=res,
        status = ResponseStatus.RETRIEVED
    )
    
@router.get("/internal_auditors", response_model=Response[InternalAuditorsChecklistListResponse])
async def get_all_internal_auditors_checklists(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.get_all_internal_auditors_checklists(
        filters=filters,
        sort=sort,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklists retrieved successfully",
        data=res,
        status = ResponseStatus.RETRIEVED
    )
    
    
@router.post("/internal_auditors/observation", response_model=Response[InternalAuditorsChecklistItem])
async def create_internal_auditors_observation(
    data: InternalAuditorsChecklistItemRequest,
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.add_internal_auditors_observation(
        data=data,
        checklist_id=checklist_id,
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item created successfully",
        data=res,
        status = ResponseStatus.CREATED
    )
    
@router.patch("/internal_auditors/observation/{item_id}", response_model=Response[InternalAuditorsChecklistItem])
async def update_internal_auditors_observation(
    item_id: UUID,
    data: InternalAuditorsChecklistItemRequest,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.update_internal_auditors_observation(
        item_id=item_id,
        data=data,
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item updated successfully",
        data=res,
        status = ResponseStatus.UPDATED
    )
    
@router.delete("/internal_auditors/observation/{item_id}", response_model=Response[InternalAuditorsChecklistItem])
async def delete_internal_auditors_observation(
    item_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.delete_internal_auditors_observation(item_id=item_id)
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item deleted successfully",
        data=res,
        status = ResponseStatus.DELETED
    )
    
    
@router.post("/internal_audit_observation", response_model=Response[InternalAuditObservationChecklist])
async def create_internal_audit_observation(
    data: InternalAuditObservationChecklistRequest,
    checklist_service: ChecklistService = Depends(get_checklist_service),
     user : User = Depends(authenticate),
):
    res = await checklist_service.add_internal_audit_observation(
        data=data,
        user_id=user.id,
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item created successfully",
        data=res,
        status = ResponseStatus.CREATED
    )
    
@router.patch("/internal_audit_observation/{checklist_id}", response_model=Response[InternalAuditObservationChecklist])
async def update_internal_audit_observation(
    checklist_id: UUID,
    data: InternalAuditObservationChecklistUpdate,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.update_internal_audit_observation(
        checklist_id=checklist_id,
        data=data,
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item updated successfully",
        data=res,
        status = ResponseStatus.UPDATED
    )
    
@router.delete("/internal_audit_observation/{checklist_id}", response_model=Response[InternalAuditObservationChecklist])
async def delete_internal_audit_observation(
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.delete_internal_audit_observation(checklist_id=checklist_id)
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item deleted successfully",
        data=res,
        status = ResponseStatus.DELETED
    )
    
@router.get("/internal_audit_observation/{checklist_id}", response_model=Response[InternalAuditObservationChecklistResponse])
async def get_internal_audit_observation_checklist_by_id(
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.get_internal_audit_observation_checklist_by_id(checklist_id=checklist_id)
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item retrieved successfully",
        data=res,
        status = ResponseStatus.RETRIEVED
    )
    
@router.get("/internal_audit_observation", response_model=Response[InternalAuditObservationChecklistListResponse])
async def get_all_internal_audit_observation_checklists(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    checklist_service: ChecklistService = Depends(get_checklist_service),
   
):
    res = await checklist_service.get_all_internal_audit_observation_checklists(
        filters=filters,
        sort=sort,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
        
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklists retrieved successfully",
        data=res,
        status = ResponseStatus.RETRIEVED
    )
    
    
@router.post("/internal_audit_observation/item", response_model=Response[InternalAuditObservationChecklistItem])
async def create_internal_audit_observation_item(
    data: InternalAuditObservationChecklistItemRequest,
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.add_internal_audit_observation_item(
        data=data,
        checklist_id=checklist_id,
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item created successfully",
        data=res,
        status = ResponseStatus.CREATED
    )
    
@router.patch("/internal_audit_observation/item/{item_id}", response_model=Response[InternalAuditObservationChecklistItem])
async def update_internal_audit_observation_item(
    item_id: UUID,
    data: InternalAuditObservationChecklistItemRequest,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.update_internal_audit_observation_item(
        item_id=item_id,
        data=data,
    )
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item updated successfully",
        data=res,
        status = ResponseStatus.UPDATED
    )
    
@router.delete("/internal_audit_observation/item/{item_id}", response_model=Response[InternalAuditObservationChecklistItem])
async def delete_internal_audit_observation_item(
    item_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.delete_internal_audit_observation_item(item_id=item_id)
    
    return Response(
        success=True,
        message="Internal Auditors Checklist item deleted successfully",
        data=res,
        status = ResponseStatus.DELETED
    )
    
@router.post("/franchise_audit", response_model=Response[FranchiseAuditChecklist])
async def create_franchise_audit_checklist(
    data: FranchiseAuditChecklistRequest,
    checklist_service: ChecklistService = Depends(get_checklist_service),
    user : User = Depends(authenticate),
):
    res = await checklist_service.add_franchise_audit_checklist(
        data=data,
        user_id=user.id,
    )
    
    return Response(
        success=True,
        message="Franchise Audit Checklist created successfully",
        data=res,
        status = ResponseStatus.CREATED
    )
    
@router.patch("/franchise_audit/{checklist_id}", response_model=Response[FranchiseAuditChecklist])
async def update_franchise_audit_checklist(
    checklist_id: UUID,
    data: FranchiseAuditChecklistUpdate,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.update_franchise_audit_checklist(
        checklist_id=checklist_id,
        data=data,
    )
    
    return Response(
        success=True,
        message="Franchise Audit Checklist updated successfully",
        data=res,
        status = ResponseStatus.UPDATED
    )
    
@router.delete("/franchise_audit/{checklist_id}", response_model=Response[FranchiseAuditChecklist])
async def delete_franchise_audit_checklist(
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.delete_franchise_audit_checklist(checklist_id=checklist_id)
    
    return Response(
        success=True,
        message="Franchise Audit Checklist deleted successfully",
        data=res,
        status = ResponseStatus.DELETED
    )
    
@router.get("/franchise_audit/{checklist_id}", response_model=Response[FranchiseAuditChecklistResponse])
async def get_franchise_audit_checklist_by_id(
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.get_franchise_audit_checklist_by_id(checklist_id=checklist_id)
    
    return Response(
        success=True,
        message="Franchise Audit Checklist retrieved successfully",
        data=res,
        status = ResponseStatus.RETRIEVED
    )
    
@router.get("/franchise_audit", response_model=Response[FranchiseAuditChecklistListResponse])
async def get_all_franchise_audit_checklists(
    filters: Optional[str] = None,
    sort: Optional[str] = "created_at.desc",
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.get_all_franchise_audit_checklists(
        filters=filters,
        sort=sort,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
    )
    
    return Response(
        success=True,
        message="Franchise Audit Checklists retrieved successfully",
        data=res,
        status = ResponseStatus.RETRIEVED
    )
    
    
@router.post("/franchise_audit/observation", response_model=Response[FranchiseAuditObservation])
async def create_franchise_audit_observation(
    data: FranchiseAuditObservationRequest,
    checklist_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.add_franchise_audit_observation(
        data=data,
        checklist_id=checklist_id,
    )
    
    return Response(
        success=True,
        message="Franchise Audit Checklist item created successfully",
        data=res,
        status = ResponseStatus.CREATED
    )
    
@router.patch("/franchise_audit/observation/{item_id}", response_model=Response[FranchiseAuditObservation])
async def update_franchise_audit_observation(
    item_id: UUID,
    data: FranchiseAuditObservationUpdate,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.update_franchise_audit_observation(
        item_id=item_id,
        data=data,
    )
    
    return Response(
        success=True,
        message="Franchise Audit Checklist item updated successfully",
        data=res,
        status = ResponseStatus.UPDATED
    )
    
@router.delete("/franchise_audit/observation/{item_id}", response_model=Response[FranchiseAuditObservation])
async def delete_franchise_audit_observation(
    item_id: UUID,
    checklist_service: ChecklistService = Depends(get_checklist_service),
):
    res = await checklist_service.delete_franchise_audit_observation(item_id=item_id)
    
    return Response(
        success=True,
        message="Franchise Audit Checklist item deleted successfully",
        data=res,
        status = ResponseStatus.DELETED
    )