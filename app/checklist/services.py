from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException,status
from app.checklist.models import (
    BRCPWarehouseChecklistListResponse,
    BRCPWarehouseChecklistRequest,
    BRCPWarehouseChecklistResponse,
    BatteryRefreshStatusResponse,
    ChargerInfrastructureResponse,
    FranchiseAuditChecklistListResponse,
    FranchiseAuditChecklistRequest,
    FranchiseAuditChecklistResponse,
    FranchiseAuditChecklistUpdate,
    FranchiseAuditObservationRequest,
    FranchiseAuditObservationResponse,
    FranchiseAuditObservationUpdate,
    InternalAuditObservationChecklistItemRequest,
    InternalAuditObservationChecklistItemResponse,
    InternalAuditObservationChecklistListResponse,
    InternalAuditObservationChecklistRequest,
    InternalAuditObservationChecklistResponse,
    InternalAuditObservationChecklistUpdate,
    InternalAuditorsChecklist,
    InternalAuditorsChecklistItem,
    InternalAuditObservationChecklist,
    InternalAuditObservationChecklistItem,
    BRCPWarehouseChecklist,
    ChargerInfrastructure,
    InternalAuditorsChecklistItemRequest,
    InternalAuditorsChecklistItemResponse,
    InternalAuditorsChecklistListResponse,
    InternalAuditorsChecklistRequested,
    InternalAuditorsChecklistResponse,
    InternalAuditorsChecklistUpdate,
    MeasuringInstrument,
    BatteryRefreshStatus,
    FranchiseAuditChecklist,
    FranchiseAuditObservation,
    MeasuringInstrumentResponse,
    WarehouseAdditionalInfo,
)
from app.core.config import settings
from app.core.mail import send_email
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.utils.dsl_filter import apply_filters, apply_sort
from app.utils.model_graph import ModelGraph
from app.utils.serializer import to_naive
from app.users.models import UserResponse, User
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload



class ChecklistService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build(
            [
                InternalAuditorsChecklist,
                InternalAuditorsChecklistItem,
                InternalAuditObservationChecklist,
                InternalAuditObservationChecklistItem,
                BRCPWarehouseChecklist,
                ChargerInfrastructure,
                MeasuringInstrument,
                BatteryRefreshStatus,
                FranchiseAuditChecklist,
                FranchiseAuditObservation,
            ]
        )
        
        
    async def create_internal_auditors_checklist(
        self,
        data: InternalAuditorsChecklistRequested,
        background_tasks,
        user_id,
    ):
        
        checklist = InternalAuditorsChecklist(
            internal_audit_number_id=data.internal_audit_number,
            division=data.division,
            audit_area=data.audit_area,
            location=data.location,
            status=data.status,
            created_by_id=user_id,
        )
        self.session.add(checklist)
        await self.session.commit()
        
        for item in data.items:
            checklist_item = InternalAuditorsChecklistItem(
                activity_description=item.activity_description,
                applicable_functions=item.applicable_functions,
                audit_findings=item.audit_findings,
                checklist_id=checklist.id,
            )
            self.session.add(checklist_item)
            await self.session.commit()
            
            
        return checklist 
    
    
    async def update_internal_auditors_checklist(
        self,
        checklist_id: UUID,
        data: InternalAuditorsChecklistUpdate,
    
    ):
        
        checklist = await self.session.execute(
            select(InternalAuditorsChecklist).where(InternalAuditorsChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        if data.internal_audit_number:
            checklist.internal_audit_number_id = data.internal_audit_number
            
        if data.division:
            checklist.division = data.division
            
        if data.audit_area:
            checklist.audit_area = data.audit_area
            
        if data.location:
            checklist.location = data.location
            
        if data.status:
            checklist.status = data.status
            
            
        if data.items:
            await self.session.execute(
                delete(InternalAuditorsChecklistItem)
                .where(InternalAuditorsChecklistItem.checklist_id == checklist.id)
            )
            
            self.session.add_all([
                InternalAuditorsChecklistItem(
                    checklist_id=checklist.id,
                    activity_description=item.activity_description,
                    applicable_functions=item.applicable_functions,
                    audit_findings=item.audit_findings,
                )
                for item in data.items
            ])
            
        await self.session.commit()
        return checklist
    
    async def delete_internal_auditors_checklist(self, checklist_id: UUID):
        checklist = await self.session.execute(
            select(InternalAuditorsChecklist).where(InternalAuditorsChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(checklist)
        await self.session.commit()
        
        return checklist
    
    async def get_internal_auditors_checklist_by_id(self, checklist_id: UUID):
        checklist = await self.session.execute(
            select(InternalAuditorsChecklist)
            .where(InternalAuditorsChecklist.id == checklist_id)
            .options(
                selectinload(InternalAuditorsChecklist.created_by),
                 selectinload(InternalAuditorsChecklist.internal_audit_number),
                selectinload(InternalAuditorsChecklist.items).options(
                    selectinload(InternalAuditorsChecklistItem.checklist)
                ),
            )
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
    
    
        return InternalAuditorsChecklistResponse(
            id=checklist.id,
            internal_audit_number=checklist.internal_audit_number,
            division=checklist.division,
            audit_area=checklist.audit_area,
            location=checklist.location,
            status=checklist.status,
            items=[
                InternalAuditorsChecklistItemResponse(
                    id=item.id,
                    activity_description=item.activity_description,
                    applicable_functions=item.applicable_functions,
                    audit_findings=item.audit_findings,
                    checklist_id=item.checklist_id,
                )
                for item in checklist.items
            ],
            created_by=checklist.created_by,
            created_at=checklist.created_at,
        )
        
    async def get_all_internal_auditors_checklists(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(InternalAuditorsChecklist).options(
            selectinload(InternalAuditorsChecklist.items).options(
                selectinload(InternalAuditorsChecklistItem.checklist)
            ),
            selectinload(InternalAuditorsChecklist.internal_audit_number),
            selectinload(InternalAuditorsChecklist.created_by),
        )
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        if from_date and to_date:
            stmt = stmt.where(
                InternalAuditorsChecklist.from_date >= from_date, InternalAuditorsChecklist.to_date <= to_date
            )
        elif from_date:
            stmt = stmt.where(InternalAuditorsChecklist.from_date >= from_date)
        elif to_date:
            stmt = stmt.where(InternalAuditorsChecklist.to_date <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, InternalAuditorsChecklist, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, InternalAuditorsChecklist, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        checklists = result.scalars().all()

        response = InternalAuditorsChecklistListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                InternalAuditorsChecklistResponse(
                    id=checklist.id,
                    internal_audit_number=checklist.internal_audit_number,
                    division=checklist.division,
                    audit_area=checklist.audit_area,
                    location=checklist.location,
                    status=checklist.status,
                    items=[
                        InternalAuditorsChecklistItemResponse(
                            id=item.id,
                            activity_description=item.activity_description,
                            applicable_functions=item.applicable_functions,
                            audit_findings=item.audit_findings,
                            checklist_id=item.checklist_id,
                        )
                        for item in checklist.items
                    ],
                    created_by=checklist.created_by,
                    created_at=checklist.created_at,
                )
                for checklist in checklists
            ],
        )
        
        return response
    
    
    async def add_internal_auditors_observation(
        self,
        data: InternalAuditorsChecklistItemRequest,
        checklist_id: UUID,
    ):
        
        checklist = await self.session.execute(
            select(InternalAuditorsChecklist).where(InternalAuditorsChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        
        
        checklist_item = InternalAuditorsChecklistItem(
            activity_description=data.activity_description,
            applicable_functions=data.applicable_functions,
            audit_findings=data.audit_findings,
            checklist_id=checklist.id,
        )
        self.session.add(checklist_item)
        await self.session.commit()
        
        return checklist_item
    
    async def delete_internal_auditors_observation(self, item_id: UUID):
        item = await self.session.execute(
            select(InternalAuditorsChecklistItem).where(InternalAuditorsChecklistItem.id == item_id)
        )
        item = item.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist item not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        self.session.delete(item)
        await self.session.commit()
        
        return item
    
    
    async def update_internal_auditors_observation(
        self,
        item_id: UUID,
        data: InternalAuditorsChecklistItemRequest,
    ):
        
        item = await self.session.execute(
            select(InternalAuditorsChecklistItem).where(InternalAuditorsChecklistItem.id == item_id)
        )
        item = item.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist item not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        if data.activity_description:
            item.activity_description = data.activity_description
            
        if data.applicable_functions:
            item.applicable_functions = data.applicable_functions
            
        if data.audit_findings:
            item.audit_findings = data.audit_findings
            
        await self.session.commit()
        return item

    async def add_internal_audit_observation(
        self,
        data: InternalAuditObservationChecklistRequest,
        user_id     : UUID,
    ):
        
        checklist = InternalAuditObservationChecklist(
            internal_audit_number_id=data.internal_audit_number,
            division=data.division,
            audit_area=data.audit_area,
            location=data.location,
            status=data.status,
            auditee_name=data.auditee_name,
            created_by_id=user_id,
        )
        self.session.add(checklist)
        await self.session.commit()
        
        for item in data.items:
            checklist_item = InternalAuditObservationChecklistItem(
                sl_no=item.sl_no,
                procedure_ref=item.procedure_ref,
                qms_check_point=item.qms_check_point,
                observation=item.observation,
                clause_no=item.clause_no,
                ncr_type=item.ncr_type,
                checklist_id=checklist.id,
            )
            self.session.add(checklist_item)
            await self.session.commit()
            
            
        return checklist
    
    async def update_internal_audit_observation(
        self,
        checklist_id: UUID,
        data: InternalAuditObservationChecklistUpdate,
    ):
        
        checklist = await self.session.execute(
            select(InternalAuditObservationChecklist).where(InternalAuditObservationChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        if data.internal_audit_number:
            checklist.internal_audit_number = data.internal_audit_number
            
        if data.division:
            checklist.division = data.division
            
        if data.audit_area:
            checklist.audit_area = data.audit_area
            
        if data.location:
            checklist.location = data.location
            
        if data.status:
            checklist.status = data.status
            
        if data.observations:
            await self.session.execute(
                delete(InternalAuditObservationChecklistItem)
                .where(InternalAuditObservationChecklistItem.checklist_id == checklist.id)
            )
            
            self.session.add_all([
                InternalAuditObservationChecklistItem(
                    checklist_id=checklist.id,
                    sl_no=item.sl_no,
                    procedure_ref=item.procedure_ref,
                    qms_check_point=item.qms_check_point,
                    observation=item.observation,
                    clause_no=item.clause_no,
                    ncr_type=item.ncr_type,
                    
                )
                for item in data.observations
            ])
            
            
        await self.session.commit()
        await self.session.refresh(checklist)
        return checklist
    
    async def delete_internal_audit_observation(self, checklist_id: UUID):
        checklist = await self.session.execute(
            select(InternalAuditObservationChecklist).where(InternalAuditObservationChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(checklist)
        await self.session.commit()
        
        return checklist
    
    async def get_internal_audit_observation_checklist_by_id(self, checklist_id: UUID):
        checklist = await self.session.execute(
            select(InternalAuditObservationChecklist)
            .where(InternalAuditObservationChecklist.id == checklist_id)
            .options(
            selectinload(InternalAuditObservationChecklist.items),
            selectinload(InternalAuditObservationChecklist.created_by),
            selectinload(InternalAuditObservationChecklist.internal_audit_number),
        )
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
    
    
        return InternalAuditObservationChecklistResponse(
            id=checklist.id,
            internal_audit_number=checklist.internal_audit_number,
            division=checklist.division,
            audit_area=checklist.audit_area,
            location=checklist.location,
            status=checklist.status,
            auditee_name=checklist.auditee_name,
            updated_at =checklist.updated_at,
            items=[
                InternalAuditObservationChecklistItemResponse(
                    id=item.id,
                    sl_no=item.sl_no,
                    procedure_ref=item.procedure_ref,
                    qms_check_point=item.qms_check_point,
                    observation=item.observation,
                    clause_no=item.clause_no,
                    ncr_type=item.ncr_type,
                    checklist_id=item.checklist_id,
                )
                for item in checklist.items
            ],
            created_by=checklist.created_by,
            created_at=checklist.created_at,
        )
        
    async def get_all_internal_audit_observation_checklists(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(InternalAuditObservationChecklist).options(
            selectinload(InternalAuditObservationChecklist.items),
            selectinload(InternalAuditObservationChecklist.created_by),
            selectinload(InternalAuditObservationChecklist.internal_audit_number),
        )
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        if from_date and to_date:
            stmt = stmt.where(
                InternalAuditObservationChecklist.from_date >= from_date, InternalAuditObservationChecklist.to_date <= to_date
            )
        elif from_date:
            stmt = stmt.where(InternalAuditObservationChecklist.from_date >= from_date)
        elif to_date:
            stmt = stmt.where(InternalAuditObservationChecklist.to_date <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, InternalAuditObservationChecklist, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, InternalAuditObservationChecklist, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        checklists = result.scalars().all()

        response = InternalAuditObservationChecklistListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                InternalAuditObservationChecklistResponse(
                    id=checklist.id,
                    internal_audit_number=checklist.internal_audit_number,
                    division=checklist.division,
                    audit_area=checklist.audit_area,
                    location=checklist.location,
                    status=checklist.status,
                     auditee_name=checklist.auditee_name,
                    items=[
                        InternalAuditObservationChecklistItemResponse(
                            id=item.id,
                            sl_no=item.sl_no,
                            procedure_ref=item.procedure_ref,
                            qms_check_point=item.qms_check_point,
                            observation=item.observation,
                            clause_no=item.clause_no,
                            ncr_type=item.ncr_type,
                            checklist_id=item.checklist_id,
                        )
                        for item in checklist.items
                    ],
                    created_by=checklist.created_by,
                    created_at=checklist.created_at,
                )
                for checklist in checklists
            ],
        )
        
        return response
    
    
    async def add_internal_audit_observation_item(
        self,
        data: InternalAuditObservationChecklistItemRequest,
        checklist_id: UUID,
    ):
        
        checklist = await self.session.execute(
            select(InternalAuditObservationChecklist).where(InternalAuditObservationChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        
        
        checklist_item = InternalAuditorsChecklistItem(
            activity_description=data.activity_description,
            applicable_functions=data.applicable_functions,
            audit_findings=data.audit_findings,
            checklist_id=checklist.id,
        )
        self.session.add(checklist_item)
        await self.session.commit()
        
        return checklist_item
    
    async def delete_internal_audit_observation_item(self, item_id: UUID):
        item = await self.session.execute(
            select(InternalAuditorsChecklistItem).where(InternalAuditorsChecklistItem.id == item_id)
        )
        item = item.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist item not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        self.session.delete(item)
        await self.session.commit()
        
        return item
    
    
    async def update_internal_audit_observation_item(
        self,
        item_id: UUID,
        data: InternalAuditObservationChecklistItemRequest,
    ):
        
        item = await self.session.execute(
            select(InternalAuditorsChecklistItem).where(InternalAuditorsChecklistItem.id == item_id)
        )
        item = item.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist item not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        if data.activity_description:
            item.activity_description = data.activity_description
            
        if data.applicable_functions:
            item.applicable_functions = data.applicable_functions
            
        if data.audit_findings:
            item.audit_findings = data.audit_findings
            
        await self.session.commit()
        return item

    async def add_franchise_audit_checklist(
        self,
        data: FranchiseAuditChecklistRequest,
        user_id: UUID,
        
    ):
        
        checklist = FranchiseAuditChecklist(
            division=data.division,
            audit_area=data.audit_area,
            location=data.location,
            franchise_name=data.franchise_name,
            audit_date=to_naive(data.audit_date),
            suggestions=data.suggestions,
            service_engineer_sign=data.service_engineer_sign,
            created_by_id=user_id,
            status=data.status,
        )
        self.session.add(checklist)
        await self.session.commit()
        
        for item in data.observations:
            checklist_item = FranchiseAuditObservation(
                section=item.section,
                sl_no=item.sl_no,
                requirement=item.requirement,
                observation=item.observation,
                checklist_id=checklist.id,
            )
            self.session.add(checklist_item)
            await self.session.commit()
            
            
        return checklist
        

    async def update_franchise_audit_checklist(
        self,
        checklist_id: UUID,
        data: FranchiseAuditChecklistUpdate,
    ):
        result = await self.session.execute(
            select(FranchiseAuditChecklist)
            .where(FranchiseAuditChecklist.id == checklist_id)
            .options(selectinload(FranchiseAuditChecklist.observations))
        )
        checklist = result.scalar_one_or_none()

        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        if data.status is not None:
            checklist.status = data.status

        if data.division is not None:
            checklist.division = data.division

        if data.audit_area is not None:
            checklist.audit_area = data.audit_area

        if data.location is not None:
            checklist.location = data.location

        if data.franchise_name is not None:
            checklist.franchise_name = data.franchise_name

        if data.audit_date is not None:
            checklist.audit_date = to_naive(data.audit_date)

        if data.suggestions is not None:
            checklist.suggestions = data.suggestions

        if data.service_engineer_sign is not None:
            checklist.service_engineer_sign = data.service_engineer_sign

        if data.observations is not None:

            await self.session.execute(
                delete(FranchiseAuditObservation)
                .where(FranchiseAuditObservation.checklist_id == checklist.id)
            )

            self.session.add_all([
                FranchiseAuditObservation(
                    checklist_id=checklist.id,
                    section=obs.section,
                    sl_no=obs.sl_no,
                    requirement=obs.requirement,
                    observation=obs.observation,
                )
                for obs in data.observations
            ])


        await self.session.commit()

        await self.session.refresh(checklist)

        return checklist
        
    async def delete_franchise_audit_checklist(self, checklist_id: UUID):
        checklist = await self.session.execute(
            select(FranchiseAuditChecklist).where(FranchiseAuditChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(checklist)
        await self.session.commit()
        
        return checklist
    
    async def get_franchise_audit_checklist_by_id(self, checklist_id: UUID):
        checklist = await self.session.execute(
            select(FranchiseAuditChecklist)
            .where(FranchiseAuditChecklist.id == checklist_id)
            .options(
                selectinload(FranchiseAuditChecklist.observations).options(
                    selectinload(FranchiseAuditObservation.checklist)
                ),
                selectinload(FranchiseAuditChecklist.created_by),
            )
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
    
    
        return FranchiseAuditChecklistResponse(
            id=checklist.id,
            division=checklist.division,
            audit_area=checklist.audit_area,
            location=checklist.location,
            franchise_name=checklist.franchise_name,
            audit_date=checklist.audit_date,
            suggestions=checklist.suggestions,
            service_engineer_sign=checklist.service_engineer_sign,
            status=checklist.status,
            observations=[
                FranchiseAuditObservationResponse(
                    id=item.id,
                    section=item.section,
                    sl_no=item.sl_no,
                    requirement=item.requirement,
                    observation=item.observation,
                )
                for item in checklist.observations
            ],
            created_by=checklist.created_by,
            created_at=checklist.created_at,
            updated_at=checklist.updated_at,
        )
        
    async def get_all_franchise_audit_checklists(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(FranchiseAuditChecklist).options(
            selectinload(FranchiseAuditChecklist.observations).options(
                selectinload(FranchiseAuditObservation.checklist)
            ),
            selectinload(FranchiseAuditChecklist.created_by),
        )
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        if from_date and to_date:
            stmt = stmt.where(
                FranchiseAuditChecklist.from_date >= from_date, FranchiseAuditChecklist.to_date <= to_date
            )
        elif from_date:
            stmt = stmt.where(FranchiseAuditChecklist.from_date >= from_date)
        elif to_date:
            stmt = stmt.where(FranchiseAuditChecklist.to_date <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, FranchiseAuditChecklist, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, FranchiseAuditChecklist, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        checklists = result.scalars().all()

        response = FranchiseAuditChecklistListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                FranchiseAuditChecklistResponse(
                    id=checklist.id,
                    division=checklist.division,
                    audit_area=checklist.audit_area,
                    location=checklist.location,
                    franchise_name=checklist.franchise_name,
                    audit_date=checklist.audit_date,
                    suggestions=checklist.suggestions,
                    service_engineer_sign=checklist.service_engineer_sign,
                    status=checklist.status,
                    observations=[
                        FranchiseAuditObservationResponse(
                            id=item.id,
                            section=item.section,
                            sl_no=item.sl_no,
                            requirement=item.requirement,
                            observation=item.observation,
                        )
                        for item in checklist.observations
                    ],
                    created_by=checklist.created_by,
                    created_at=checklist.created_at,
                    updated_at=checklist.updated_at,
                )
                for checklist in checklists
            ],    
        )
        
        return response
    
    
    async def add_franchise_audit_observation(
        self,
        data: FranchiseAuditObservationRequest,
        checklist_id: UUID,
    ):
        
        checklist = await self.session.execute(
            select(FranchiseAuditChecklist).where(FranchiseAuditChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        
        
        checklist_item = FranchiseAuditObservation(
            section=data.section,
            sl_no=data.sl_no,
            requirement=data.requirement,
            observation=data.observation,
            checklist_id=checklist.id,
        )
        self.session.add(checklist_item)
        await self.session.commit()
        
        return checklist_item
    
    async def delete_franchise_audit_observation(self, item_id: UUID):
        item = await self.session.execute(
            select(FranchiseAuditObservation).where(FranchiseAuditObservation.id == item_id)
        )
        item = item.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist item not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        self.session.delete(item)
        await self.session.commit()
        
        return item
    
    
    async def update_franchise_audit_observation(
        self,
        item_id: UUID,
        data: FranchiseAuditObservationUpdate,
    ):
        
        item = await self.session.execute(
            select(FranchiseAuditObservation).where(FranchiseAuditObservation.id == item_id)
        )
        item = item.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist item not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        if data.section:
            item.section = data.section
            
        if data.sl_no:
            item.sl_no = data.sl_no
            
        if data.requirement:
            item.requirement = data.requirement
            
        if data.observation:
            item.observation = data.observation
            
        await self.session.commit()    
        return item
    
    async def create_brcp_warehouse_checklist(
        self,
        data: BRCPWarehouseChecklistRequest,
        user_id: UUID,
    ):
        
        checklist = BRCPWarehouseChecklist(
            internal_audit_number=data.internal_audit_number,
            warehouse_incharge=data.warehouse_incharge,
            supplier=data.supplier,
            status=data.status,
            created_by_id=user_id,
        )
        self.session.add(checklist)
        await self.session.commit()
        
        for item in data.chargers:
            checklist_item = ChargerInfrastructure(
                type=item.type,
                charger_serial_no=item.charger_serial_no,
                make=item.make,
                year_of_mfg=item.year_of_mfg,
                rating=item.rating,
                channels_working=item.channels_working,
                channels_not_working=item.channels_not_working,
                calibration_due_on=item.calibration_due_on,
                work_instruction_available=item.work_instruction_available,
                checklist_id=checklist.id,
            )
            self.session.add(checklist_item)
            await self.session.commit()
            
            
        for item in data.instruments:
            checklist_item = MeasuringInstrument(
                instrument_name=item.instrument_name,
                imte_no=item.imte_no,
                make=item.make,
                serial_no=item.serial_no,
                calibration_due_on=item.calibration_due_on,
                checklist_id=checklist.id,
            )
            self.session.add(checklist_item)
            await self.session.commit()
            
            
        for item in data.batteries:
            checklist_item = BatteryRefreshStatus(
                type=item.type,
                model=item.model,
                total_due_qty=item.total_due_qty,
                ageing_91_180=item.ageing_91_180,
                refresh_91_180_date=item.refresh_91_180_date,
                ageing_181_270=item.ageing_181_270,
                refresh_181_270_date=item.refresh_181_270_date,
                ageing_271_360=item.ageing_271_360,
                refresh_271_360_date=item.refresh_271_360_date,
                ageing_361_450=item.ageing_361_450,
                refresh_361_450_date=item.refresh_361_450_date,
                ageing_451_540=item.ageing_451_540,
                refresh_451_540_date=item.refresh_451_540_date,
                ageing_above_540=item.ageing_above_540,
                remarks=item.remarks,
                checklist_id=checklist.id,
            )
            self.session.add(checklist_item)
            await self.session.commit()
            
            
        for item in data.additional_info:
            checklist_item = WarehouseAdditionalInfo(
                operating_by=item.operating_by,
                total_manpower=item.total_manpower,
                refresh_charging_manpower=item.refresh_charging_manpower,
                power_cut_hours_per_day=item.power_cut_hours_per_day,
                dg_available=item.dg_available,
                additional_information=item.additional_information,
                checklist_id=checklist.id,
            )
            self.session.add(checklist_item)
            await self.session.commit()
            
            
        return checklist
    
    
    async def get_brcp_warehouse_checklist_by_id(self, checklist_id: UUID):
        
        checklist = await self.session.execute(
            select(BRCPWarehouseChecklist)
            .where(BRCPWarehouseChecklist.id == checklist_id)
            .options(
                selectinload(BRCPWarehouseChecklist.chargers).options(
                    selectinload(ChargerInfrastructure.checklist)
                ),
                selectinload(BRCPWarehouseChecklist.instruments).options(
                    selectinload(MeasuringInstrument.checklist)
                ),
                selectinload(BRCPWarehouseChecklist.batteries).options(
                    selectinload(BatteryRefreshStatus.checklist)
                ),
                selectinload(BRCPWarehouseChecklist.additional_info).options(
                    selectinload(WarehouseAdditionalInfo.checklist)
                ),
                selectinload(BRCPWarehouseChecklist.created_by),
            )
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
    
    
        return BRCPWarehouseChecklistResponse(
            id=checklist.id,
            internal_audit_number=checklist.internal_audit_number,
            warehouse_incharge=checklist.warehouse_incharge,
            supplier=checklist.supplier,
            status=checklist.status,
            chargers=[
                ChargerInfrastructureResponse(
                    id=item.id,
                    type=item.type,
                    charger_serial_no=item.charger_serial_no,
                    make=item.make,
                    year_of_mfg=item.year_of_mfg,
                    rating=item.rating,
                    channels_working=item.channels_working,
                    channels_not_working=item.channels_not_working,
                    calibration_due_on=item.calibration_due_on,
                    work_instruction_available=item.work_instruction_available,
                    checklist_id=item.checklist_id,
                )
                for item in checklist.chargers
            ],
            instruments=[
                MeasuringInstrumentResponse(
                    id=item.id,
                    instrument_name=item.instrument_name,
                    imte_no=item.imte_no,
                    make=item.make,
                    serial_no=item.serial_no,
                    calibration_due_on=item.calibration_due_on,
                    checklist_id=item.checklist_id,
                )
                for item in checklist.instruments
            ],
            batteries=[
                BatteryRefreshStatusResponse(
                    id=item.id,
                    type=item.type,
                    model=item.model,
                    total_due_qty=item.total_due_qty,
                    ageing_91_180=item.ageing_91_180,
                    refresh_91_180_date=item.refresh_91_180_date,
                    ageing_181_270=item.ageing_181_270,
                    refresh_181_270_date=item.refresh_181_270_date,
                    ageing_271_360=item.ageing_271_360,
                    refresh_271_360_date=item.refresh_271_360_date,
                    ageing_361_450=item.ageing_361_450,
                    refresh_361_450_date=item.refresh_361_450_date,
                    ageing_451_540=item.ageing_451_540,
                    refresh_451_540_date=item.refresh_451_540_date,
                    ageing_above_540=item.ageing_above_540,
                    remarks=item.remarks,
                    checklist_id=item.checklist_id,
                )
                for item in checklist.batteries
            ],
            additional_info=checklist.additional_info,
            created_by=checklist.created_by,
            created_at=checklist.created_at,
            updated_at=checklist.updated_at,
        )
        
    async def get_all_brcp_warehouse_checklists(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(BRCPWarehouseChecklist).options(
            selectinload(BRCPWarehouseChecklist.chargers).options(
                selectinload(ChargerInfrastructure.checklist)
            ),
            selectinload(BRCPWarehouseChecklist.instruments).options(
                selectinload(MeasuringInstrument.checklist)
            ),
            selectinload(BRCPWarehouseChecklist.batteries).options(
                selectinload(BatteryRefreshStatus.checklist)
            ),
            selectinload(BRCPWarehouseChecklist.additional_info).options(
                selectinload(WarehouseAdditionalInfo.checklist)
            ),
            selectinload(BRCPWarehouseChecklist.created_by),
        )
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        if from_date and to_date:
            stmt = stmt.where(
                BRCPWarehouseChecklist.from_date >= from_date, BRCPWarehouseChecklist.to_date <= to_date
            )
        elif from_date:
            stmt = stmt.where(BRCPWarehouseChecklist.from_date >= from_date)
        elif to_date:
            stmt = stmt.where(BRCPWarehouseChecklist.to_date <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, BRCPWarehouseChecklist, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, BRCPWarehouseChecklist, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        checklists = result.scalars().all()

        response = BRCPWarehouseChecklistListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                BRCPWarehouseChecklistResponse(
                    id=checklist.id,
                    internal_audit_number=checklist.internal_audit_number,
                    warehouse_incharge=checklist.warehouse_incharge,
                    supplier=checklist.supplier,
                    status=checklist.status,
                    chargers=[
                        ChargerInfrastructureResponse(
                            id=item.id,
                            type=item.type,
                            charger_serial_no=item.charger_serial_no,
                            make=item.make,
                            year_of_mfg=item.year_of_mfg,
                            rating=item.rating,
                            channels_working=item.channels_working,
                            channels_not_working=item.channels_not_working,
                            calibration_due_on=item.calibration_due_on,
                            work_instruction_available=item.work_instruction_available,
                            checklist_id=item.checklist_id,
                        )
                        for item in checklist.chargers
                    ],
                    instruments=[
                        MeasuringInstrumentResponse(
                            id=item.id,
                            instrument_name=item.instrument_name,
                            imte_no=item.imte_no,
                            make=item.make,
                            serial_no=item.serial_no,
                            calibration_due_on=item.calibration_due_on,
                            checklist_id=item.checklist_id,
                        )
                        for item in checklist.instruments
                    ],
                    batteries=[
                        BatteryRefreshStatusResponse(
                            id=item.id,
                            type=item.type,
                            model=item.model,
                            total_due_qty=item.total_due_qty,
                            ageing_91_180=item.ageing_91_180,
                            refresh_91_180_date=item.refresh_91_180_date,
                            ageing_181_270=item.ageing_181_270,
                            refresh_181_270_date=item.refresh_181_270_date,
                            ageing_271_360=item.ageing_271_360,
                            refresh_271_360_date=item.refresh_271_360_date,
                            ageing_361_450=item.ageing_361_450,
                            refresh_361_450_date=item.refresh_361_450_date,
                            ageing_451_540=item.ageing_451_540,
                            refresh_451_540_date=item.refresh_451_540_date,
                            ageing_above_540=item.ageing_above_540,
                            remarks=item.remarks,
                            checklist_id=item.checklist_id,
                        )
                        for item in checklist.batteries
                    ],
                    additional_info=checklist.additional_info,
                    created_by=checklist.created_by,
                    created_at=checklist.created_at,
                    updated_at=checklist.updated_at,
                )
                for checklist in checklists
            ],
        )
        
        
        return response
            
            
    async def update_brcp_warehouse_checklist(
        self,
        checklist_id: UUID,
        data: BRCPWarehouseChecklistRequest,
    ):
        checklist = await self.session.execute(
            select(BRCPWarehouseChecklist).where(BRCPWarehouseChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        
        if data.internal_audit_number:
            checklist.internal_audit_number = data.internal_audit_number
            
        if data.warehouse_incharge:
            checklist.warehouse_incharge = data.warehouse_incharge
            
        if data.supplier:
            checklist.supplier = data.supplier
            
        if data.status:
            checklist.status = data.status
            
        
        if data.chargers:
            await self.session.execute(
                delete(ChargerInfrastructure)
                .where(ChargerInfrastructure.checklist_id == checklist.id)
            )
            
            self.session.add_all([
                ChargerInfrastructure(
                    checklist_id=checklist.id,
                    type=item.type,
                    charger_serial_no=item.charger_serial_no,
                    make=item.make,
                    year_of_mfg=item.year_of_mfg,
                    rating=item.rating,
                    channels_working=item.channels_working,
                    channels_not_working=item.channels_not_working,
                    calibration_due_on=item.calibration_due_on,
                    work_instruction_available=item.work_instruction_available,
                )
                for item in data.chargers
            ])
            
        if data.instruments:
            await self.session.execute(
                delete(MeasuringInstrument)
                .where(MeasuringInstrument.checklist_id == checklist.id)
            )
            
            self.session.add_all([
                MeasuringInstrument(
                    checklist_id=checklist.id,
                    instrument_name=item.instrument_name,
                    imte_no=item.imte_no,
                    make=item.make,
                    serial_no=item.serial_no,
                    calibration_due_on=item.calibration_due_on,
                )
                for item in data.instruments
            ])
            
        if data.batteries:
            await self.session.execute(
                delete(BatteryRefreshStatus)
                .where(BatteryRefreshStatus.checklist_id == checklist.id)
            )
            
            self.session.add_all([
                BatteryRefreshStatus(
                    checklist_id=checklist.id,
                    type=item.type,
                    model=item.model,
                    total_due_qty=item.total_due_qty,
                    ageing_91_180=item.ageing_91_180,
                    refresh_91_180_date=item.refresh_91_180_date,
                    ageing_181_270=item.ageing_181_270,
                    refresh_181_270_date=item.refresh_181_270_date,
                    ageing_271_360=item.ageing_271_360,
                    refresh_271_360_date=item.refresh_271_360_date,
                    ageing_361_450=item.ageing_361_450,
                    refresh_361_450_date=item.refresh_361_450_date,
                    ageing_451_540=item.ageing_451_540,
                    refresh_451_540_date=item.refresh_451_540_date,
                    ageing_above_540=item.ageing_above_540,
                    remarks=item.remarks,
                )
                for item in data.batteries
            ])
            
        if data.additional_info:
            await self.session.execute(
                delete(WarehouseAdditionalInfo)
                .where(WarehouseAdditionalInfo.checklist_id == checklist.id)
            )
            
            self.session.add_all([
                WarehouseAdditionalInfo(
                    checklist_id=checklist.id,
                    operating_by=item.operating_by,
                    total_manpower=item.total_manpower,
                    refresh_charging_manpower=item.refresh_charging_manpower,
                    power_cut_hours_per_day=item.power_cut_hours_per_day,
                    dg_available=item.dg_available,
                    additional_information=item.additional_information,
                )
                for item in data.additional_info
            ])
            
            
        await self.session.commit()
        await self.session.refresh(checklist)
        return checklist
    
    async def delete_brcp_warehouse_checklist(self, checklist_id: UUID):
        checklist = await self.session.execute(
            select(BRCPWarehouseChecklist).where(BRCPWarehouseChecklist.id == checklist_id)
        )
        checklist = checklist.scalar_one_or_none()
        if not checklist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Checklist not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(checklist)
            
        await self.session.commit()
        
        return checklist