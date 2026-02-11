

from datetime import datetime
from typing import Optional
from fastapi import Depends,APIRouter
from app.core.schemas import Response, ResponseStatus
from app.dashboard.dependencies import get_dashboard_service
from app.dashboard.models import AdminDashboardResponse, AuditDashboardResponse, AuditInfoDashboardResponse, AuditeeDashboardResponse, AuditorDashboardResponse, HodDashboardResponse
from app.dashboard.services import DashboardService


router = APIRouter()


@router.get("/admin", response_model=Response[AdminDashboardResponse])
async def get_admin_dashboard(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    service: DashboardService = Depends(get_dashboard_service)):
    res = await service.get_admin_dashboard(
        from_date=from_date,
        to_date=to_date,
    )
    
    return Response(
        message= " Dashboard data fetched successfully",
       
        status=ResponseStatus.SUCCESS,
        success=True,
        data= res,)
    
    
@router.get("/auditor", response_model=Response[AuditorDashboardResponse])
async def get_auditor_dashboard(
    auditor_id: str,
    department_ids: str,
    service: DashboardService = Depends(get_dashboard_service)):
    res = await service.get_auditor_dashboard(
        auditor_id,
        department_ids,
    )
    
    return Response(
        message= " Dashboard data fetched successfully",
       
        status=ResponseStatus.SUCCESS,
        success=True,
        
        data= res,)
    
    
@router.get("/hod", response_model=Response[HodDashboardResponse])
async def get_hod_dashboard(
    plant_id: str,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    service: DashboardService = Depends(get_dashboard_service)):
    res = await service.get_hod_dashboard(
        plant_id,
        from_date=from_date,
        to_date=to_date,
    )
    
    return Response(
        message= " Dashboard data fetched successfully",
       
        status=ResponseStatus.SUCCESS,
        success=True,
        
        data= res,)
    
    
@router.get("/auditee", response_model=Response[AuditeeDashboardResponse])
async def get_auditee_dashboard(
    auditee_id: str,
    department_ids: str,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    service: DashboardService = Depends(get_dashboard_service)):
    res = await service.get_auditee_dashboard(
        auditee_id,
        department_ids = department_ids,
        from_date=from_date,
        to_date=to_date,
    )
    
    return Response(
        message= " Dashboard data fetched successfully",
       
        status=ResponseStatus.SUCCESS,
        success=True,
        
        data= res,)
    
    
    
@router.get("/audit", response_model=Response[AuditDashboardResponse])
async def get_audit_dashboard(
    audit_id: str,
    service: DashboardService = Depends(get_dashboard_service)):
    res = await service.get_audit_dashboard(
        audit_id,
    )
    
    return Response(
        message= " Dashboard data fetched successfully",
       
        status=ResponseStatus.SUCCESS,
        success=True,
        
        data= res,)
    
    
@router.get("/audit_info", response_model=Response[AuditInfoDashboardResponse])
async def get_audit_info_dashboard(
    audit_info_id: str,
    service: DashboardService = Depends(get_dashboard_service)):
    res = await service.get_audit_info_dashboard(
        audit_info_id,
    )
    
    return Response(
        message= " Dashboard data fetched successfully",
       
        status=ResponseStatus.SUCCESS,
        success=True,
        
        data= res,)