
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.schemas import ResponseStatus,Response
from app.core.security import authenticate
from app.suggestions.dependencies import get_suggestion_service
from app.suggestions.models import Suggestion, SuggestionCreateRequest, SuggestionListResponse, SuggestionResponse, SuggestionTeam, SuggestionTeamCreateRequest, SuggestionUpdateRequest
from app.suggestions.services import SuggestionService
from app.users.models import User

router = APIRouter()


@router.get("", response_model=Response[SuggestionListResponse])
async def get_all_suggestions(
    service: SuggestionService = Depends(get_suggestion_service),   
    filters: Optional[str] = None,
    sort: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
):
    data = await service.get_all_suggestions(
        filters=filters,
        sort=sort,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    
    return Response(
        message="Suggestions retrieved successfully",
        status=ResponseStatus.SUCCESS,
        data=data,
        success=True,
    )


@router.post("", response_model=Response[Suggestion])
async def create_suggestion(
        suggestion: SuggestionCreateRequest,
        background_tasks: BackgroundTasks,
    service: SuggestionService = Depends(get_suggestion_service),

    user : User = Depends(authenticate),
):
    data = await service.create_suggestion(suggestion,user.id,background_tasks)
    return Response(
        message="Suggestion created successfully",
        status=ResponseStatus.SUCCESS,
        data=data,
        success=True,
    )


@router.patch("/{id}", response_model=Response[Suggestion])
async def update_suggestion(
    id: UUID,
    suggestion: SuggestionUpdateRequest,
    background_tasks: BackgroundTasks,
    user : User = Depends(authenticate),
    service: SuggestionService = Depends(get_suggestion_service),
):
    data =await service.update_suggestion(id, suggestion, user.id, background_tasks)
    return Response(
        message="Suggestion updated successfully",
        status=ResponseStatus.SUCCESS,
        data=data,
        success=True,
    )
    
@router.delete("/{id}", response_model=Response[Suggestion])
async def delete_suggestion(
    id: UUID,
    service: SuggestionService = Depends(get_suggestion_service),
):
    data = await service.delete_suggestion(id)
    return Response(
        message="Suggestion deleted successfully",
        status=ResponseStatus.SUCCESS,
        data=data,
        success=True,
    )
    
@router.get("/export/all", response_model=Response[List[SuggestionResponse]])
async def export_all_suggestions(
    service: SuggestionService = Depends(get_suggestion_service),
    filters: Optional[str] = None,
    sort: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    data = await service.export_all_suggestions(
        filters=filters,
        sort=sort,
        from_date=from_date,
        to_date=to_date,
      
    )
    
    return Response(
        message="Suggestions retrieved successfully",
        status=ResponseStatus.SUCCESS,
        data=data,
        success=True,
    )
    
@router.post("/team/add",response_model=Response[SuggestionTeam])
async def add_suggestion_team(
    team: SuggestionTeamCreateRequest,
    user : User = Depends(authenticate),
    service: SuggestionService = Depends(get_suggestion_service),
):
    data = await service.add_suggestion_team(team)
    return Response(
        message="Suggestion team added successfully",
        status=ResponseStatus.SUCCESS,
        data=data,
        success=True,
    )
    
@router.delete("/team/{id}",response_model=Response[SuggestionTeam])
async def delete_suggestion_team(
    id: UUID,
    user : User = Depends(authenticate),
    service: SuggestionService = Depends(get_suggestion_service),
):
    data = await service.delete_suggestion_team(id)
    return Response(
        message="Suggestion team deleted successfully",
        status=ResponseStatus.SUCCESS,
        data=data,
        success=True,
    )



@router.post("/update/bulk",response_model=Response[Suggestion])

async def upload_excel_in_background(
        background_tasks: BackgroundTasks,
    file : UploadFile = File(...),
    user : User = Depends(authenticate),

    service: SuggestionService = Depends(get_suggestion_service),
   
):    
    return await service.upload_excel_in_background(background_tasks=background_tasks,file=await file.read(),    user_id=user.id)   