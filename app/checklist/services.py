from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException,status
from app.checklist.models import (
    FranchiseAuditChecklistListResponse,
    FranchiseAuditChecklistRequest,
    FranchiseAuditChecklistResponse,
    FranchiseAuditChecklistUpdate,
    FranchiseAuditObservationRequest,
    FranchiseAuditObservationResponse,
    FranchiseAuditObservationUpdate,
    InternalAuditObservationChecklistItemRequest,
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
)
from app.core.config import settings
from app.core.mail import send_email
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.utils.dsl_filter import apply_filters, apply_sort
from app.utils.model_graph import ModelGraph
from app.utils.serializer import to_naive
from app.users.models import UserResponse, User
from sqlalchemy import func, select
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
    ):
        
        checklist = InternalAuditorsChecklist(
            internal_audit_number=data.internal_audit_number,
            division=data.division,
            audit_area=data.audit_area,
            location=data.location,
            status=data.status,
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
            checklist.internal_audit_number = data.internal_audit_number
            
        if data.division:
            checklist.division = data.division
            
        if data.audit_area:
            checklist.audit_area = data.audit_area
            
        if data.location:
            checklist.location = data.location
            
        if data.status:
            checklist.status = data.status
            
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
        
    ):
        
        checklist = InternalAuditObservationChecklist(
            internal_audit_number=data.internal_audit_number,
            division=data.division,
            audit_area=data.audit_area,
            location=data.location,
            status=data.status,
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
            
        await self.session.commit()
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
                selectinload(InternalAuditObservationChecklist.items).options(
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
    
    
        return InternalAuditObservationChecklistResponse(
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
            selectinload(InternalAuditObservationChecklist.items).options(
                selectinload(InternalAuditorsChecklistItem.checklist)
            ),
            selectinload(InternalAuditObservationChecklist.created_by),
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
        
    ):
        
        checklist = FranchiseAuditChecklist(
            division=data.division,
            audit_area=data.audit_area,
            location=data.location,
            franchise_name=data.franchise_name,
            audit_date=data.audit_date,
            suggestions=data.suggestions,
            service_engineer_sign=data.service_engineer_sign,
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
        
        if data.division:
            checklist.division = data.division
            
        if data.audit_area:
            checklist.audit_area = data.audit_area
            
        if data.location:
            checklist.location = data.location
            
        if data.franchise_name:
            checklist.franchise_name = data.franchise_name
            
        if data.audit_date:
            checklist.audit_date = data.audit_date
            
        if data.suggestions:
            checklist.suggestions = data.suggestions
            
        if data.service_engineer_sign:
            checklist.service_engineer_sign = data.service_engineer_sign
            
        await self.session.commit()
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
    
    