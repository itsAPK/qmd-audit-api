from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.schemas import Response, ResponseStatus
from app.ncr.models import (
    NCR,
    ClauseNCRStatsResponse,
    CreateDocumentReferenceRequest,
    DepartmentWiseNCRStatsResponse,
    NCRClauses,
    NCRClausesRequest,
    NCRCreateRequest,
    NCRFileType,
    NCRFiles,
    NCRListResponse,
    NCRResponse,
    NCRShiftCreateRequest,
    NCRShift,
    NCRStatusResponse,
    NCRTeamCreateRequest,
    NCRUpdateRequest,
)
from app.ncr.services import NCRService
from app.ncr.dependencies import get_ncr_service
from app.core.security import authenticate
from app.users.models import User
from app.utils.upload import save_file

router = APIRouter()


@router.post("", response_model=Response[NCR])
async def create_ncr(
    data: NCRCreateRequest,
    background_tasks : BackgroundTasks,
    ncr_service: NCRService = Depends(get_ncr_service),
    user: User = Depends(authenticate),
):
    ncr = await ncr_service.create_ncr(data, user.id,background_tasks)
    return Response(
        message="NCR created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr,
    )


@router.get("", response_model=Response[NCRListResponse])
async def get_all_ncrs(
    filters: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncrs = await ncr_service.get_all_ncrs(
        filters, sort, from_date, to_date, page, page_size
    )
    return Response(
        message="NCRs fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncrs,
    )


@router.get("/export", response_model=Response[list[NCRResponse]])
async def export_all_ncrs(
    filters: Optional[str] = None,
    sort: Optional[str] = None,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncrs = await ncr_service.export_all_ncrs(filters, sort)
    return Response(
        message="NCRs fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncrs,
    )


@router.get("/{ncr_id}", response_model=Response[NCRResponse])
async def get_ncr(
    ncr_id: UUID,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncr = await ncr_service.get_ncr(ncr_id)
    return Response(
        message="NCR fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr,
    )


@router.patch("/{ncr_id}", response_model=Response[NCR])
async def update_ncr(
    ncr_id: UUID,
    data: NCRUpdateRequest,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncr = await ncr_service.update_ncr(ncr_id, data)
    return Response(
        message="NCR updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr,
    )


@router.delete("/{ncr_id}", response_model=Response[bool])
async def delete_ncr(ncr_id: UUID, ncr_service: NCRService = Depends(get_ncr_service)):
    ncr = await ncr_service.delete_ncr(ncr_id)
    return Response(
        message="NCR deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.post("/{ncr_id}/files", response_model=Response[NCRFiles])
async def upload_files(
    ncr_id: UUID,
    file_type: NCRFileType,
    file: UploadFile = File(...),
    ncr_service: NCRService = Depends(get_ncr_service),
):
    file_path = save_file(file.file, filename=file.filename)
    ncr = await ncr_service.upload_files(ncr_id, file_path, file_type)
    return Response(
        message="File uploaded successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr,
    )


@router.delete("/{ncr_id}/files/{file_id}", response_model=Response[bool])
async def delete_file(
    ncr_id: UUID, file_id: UUID, ncr_service: NCRService = Depends(get_ncr_service)
):
    ncr = await ncr_service.delete_file(ncr_id, file_id)
    return Response(
        message="File deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.post("/{ncr_id}/document-references", response_model=Response[NCR])
async def add_document_reference(
    ncr_id: UUID,
    document_reference: CreateDocumentReferenceRequest,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncr = await ncr_service.add_document_reference(ncr_id, document_reference)
    return Response(
        message="Document reference added successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr,
    )


@router.delete(
    "/{ncr_id}/document-references/{document_reference_id}",
    response_model=Response[bool],
)
async def delete_document_reference(
    ncr_id: UUID,
    document_reference_id: UUID,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncr = await ncr_service.delete_document_reference(ncr_id, document_reference_id)
    return Response(
        message="Document reference deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.post("/ncr-team", response_model=Response[NCR])
async def add_ncr_team(
    team: NCRTeamCreateRequest,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncr = await ncr_service.add_ncr_team(team)
    return Response(
        message="NCR team added successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr,
    )


@router.delete("/{ncr_id}/ncr-team/{team_id}", response_model=Response[bool])
async def delete_ncr_team(
    ncr_id: UUID,
    team_id: UUID,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncr = await ncr_service.delete_ncr_team(ncr_id, team_id)
    return Response(
        message="NCR team member deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.get("/stats/clauses", response_model=Response[ClauseNCRStatsResponse])
async def get_clause_ncr_stats(
    plant_id: Optional[UUID] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    res = await ncr_service.get_clause_ncr_stats(plant_id, from_date, to_date)
    return Response(
        message="Clauses fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=res,
    )


@router.get(
    "/stats/clauses/department-wise",
    response_model=Response[DepartmentWiseNCRStatsResponse],
)
async def get_clause_ncr_stats_department_wise(
    plant_id: Optional[UUID] = None,
    audit_id: Optional[UUID] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    res = await ncr_service.get_clause_ncr_stats_department_wise(
        plant_id, audit_id, created_from, created_to
    )
    return Response(
        message="Clauses fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=res,
    )


@router.get("/stats/companies", response_model=Response[list[NCRStatusResponse]])
async def get_company_status_counts(
    company_id: Optional[UUID] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    res = await ncr_service.get_company_status_counts(company_id, from_date, to_date)
    return Response(
        message="Company status fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=res,
    )


@router.get("/stats/plants", response_model=Response[list[NCRStatusResponse]])
async def get_plant_status_counts(
    plant_id: Optional[UUID] = None,
    company_id: Optional[UUID] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    res = await ncr_service.get_plant_status_counts(
        plant_id=plant_id,
        from_date=from_date,
        to_date=to_date,
        company_id=company_id,
        
        )
    return Response(
        message="Plant status fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=res,
    )


@router.get("/stats/departments", response_model=Response[list[NCRStatusResponse]])
async def get_department_status_counts(
    plant_id: Optional[UUID] = None,
    audit_id : Optional[UUID] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    res = await ncr_service.get_department_status_counts(
        plant_id = plant_id, from_date = from_date, to_date = to_date, audit_id = audit_id
    )
    return Response(
        message="Department status fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=res,
    )


@router.post("/config/shifts", response_model=Response[NCRShift])
async def create_shift(
    data: NCRShiftCreateRequest, ncr_service: NCRService = Depends(get_ncr_service)
):
    ncr_shift = await ncr_service.create_shift(data)
    return Response(
        message="Shift created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr_shift,
    )


@router.get("/config/shifts", response_model=Response[list[NCRShift]])
async def get_all_shifts(ncr_service: NCRService = Depends(get_ncr_service)):
    ncr_shifts = await ncr_service.get_all_shifts()
    return Response(
        message="Shifts fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr_shifts,
    )


@router.patch("/config/shifts/{shift_id}", response_model=Response[NCRShift])
async def update_shift(
    shift_id: UUID,
    data: NCRShiftCreateRequest,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncr_shift = await ncr_service.update_shift(shift_id, data)
    return Response(
        message="Shift updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr_shift,
    )


@router.delete("/config/shifts/{shift_id}", response_model=Response[bool])
async def delete_shift(
    shift_id: UUID, ncr_service: NCRService = Depends(get_ncr_service)
):
    ncr_shift = await ncr_service.delete_shift(shift_id)
    return Response(
        message="Shift deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.post("/config/clauses", response_model=Response[NCRClauses])
async def create_clause(
    data: NCRClausesRequest, ncr_service: NCRService = Depends(get_ncr_service)
):
    ncr_clause = await ncr_service.add_clause(data)
    return Response(
        message="Clause created successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr_clause,
    )


@router.get("/config/clauses", response_model=Response[list[NCRClauses]])
async def get_all_clauses(ncr_service: NCRService = Depends(get_ncr_service)):
    res = await ncr_service.get_clauses()
    return Response(
        message="Clauses fetched successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=res,
    )


@router.patch("/config/clauses/{clause_id}", response_model=Response[NCRClauses])
async def update_clause(
    clause_id: UUID,
    data: NCRClausesRequest,
    ncr_service: NCRService = Depends(get_ncr_service),
):
    ncr_clause = await ncr_service.update_clause(clause_id, data)
    return Response(
        message="Clause updated successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=ncr_clause,
    )


@router.delete("/config/clauses/{clause_id}", response_model=Response[bool])
async def delete_clause(
    clause_id: UUID, ncr_service: NCRService = Depends(get_ncr_service)
):
    ncr_clause = await ncr_service.delete_clause(clause_id)
    return Response(
        message="Clause deleted successfully",
        status=ResponseStatus.SUCCESS,
        success=True,
        data=True,
    )


@router.post("/bulk/update")
async def upload_ncr_excel(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    service : NCRService = Depends(get_ncr_service),
    user : User = Depends(authenticate),
):
    file_bytes = await file.read()

    return await service.upload_excel_in_background(
        background_tasks,
        file_bytes,
        user.id)
