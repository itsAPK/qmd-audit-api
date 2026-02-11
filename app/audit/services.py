from typing import Optional
from uuid import UUID
from app.audit.models import (
    Audit,
    AuditListResponse,
    AuditRequest,
    AuditResponse,
    AuditSchedule,
    AuditSettingsRequest,
    AuditStandard,
    AuditType,
    AuditTypeRequest,
    AuditUpdateRequest,
)
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from fastapi import HTTPException, status
from sqlalchemy import select

from app.audit_info.models import AuditInfo, AuditTeam
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.ncr.models import NCR, NCRStatus
from app.settings.links import UserDepartment
from app.settings.models import (
    Company,
    CompanyResponse,
    Department,
    DepartmentResponse,
    Plant,
    PlantResponse,
)
from app.utils.serializer import to_naive
from app.utils.model_graph import ModelGraph
from app.utils.dsl_filter import apply_filters, apply_sort


class AuditService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build([Audit, AuditInfo, AuditTeam, NCR, Department, Plant, Company])

    async def create_audit(self, data: AuditRequest, user_id: UUID):
        user_department = await self.session.execute(
            select(UserDepartment)
            .where(
                UserDepartment.user_id == user_id,
                UserDepartment.department_id == data.department_id,
            )
            .options(
                selectinload(UserDepartment.department).options(
                    selectinload(Department.plant).options(selectinload(Plant.company))
                )
            )
        )

        department = user_department.scalar_one_or_none()

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User Department not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        audit_ref = f"{datetime.now().year}-{datetime.now().year + 1}/{data.type}{data.schedule}/{department.department.plant.company.code}-{department.department.plant.code}"

        new_audit = Audit(
            ref=audit_ref,
            type=data.type,
            standard=data.standard,
            schedule=data.schedule,
            start_date=to_naive(data.start_date),
            end_date=to_naive(data.end_date),
            remarks=data.remarks,
            plant_id=department.department.plant_id,
        )
        self.session.add(new_audit)
        await self.session.commit()
        return new_audit

    async def get_all_audits(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(Audit).options(
            selectinload(Audit.plant).options(selectinload(Plant.company))
        )

        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        print(from_date, to_date)
        if from_date and to_date:
            stmt = stmt.where(
                Audit.start_date >= from_date, Audit.end_date <= to_date
            )
        elif from_date:
            stmt = stmt.where(Audit.start_date >= from_date)
        elif to_date:
            stmt = stmt.where(Audit.end_date <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, Audit, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, Audit, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        audits = result.scalars().all()

        response = AuditListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                AuditResponse(
                    id=audit.id,
                    ref=audit.ref,
                    type=audit.type,
                    standard=audit.standard,
                    schedule=audit.schedule,
                    start_date=audit.start_date,
                    end_date=audit.end_date,
                    remarks=audit.remarks,
                    plant_id=audit.plant_id,
                    plant=PlantResponse(
                        id=audit.plant_id,
                        name=audit.plant.name,
                        code=audit.plant.code,
                        company_id=audit.plant.company_id,
                        company=CompanyResponse(
                            id=audit.plant.company_id,
                            name=audit.plant.company.name,
                            code=audit.plant.company.code,
                            plants=[],
                        ),
                        departments=[],
                    ),
                )
                for audit in audits
            ],
        )

        return response

    async def export_all_audits(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(Audit).options(
            selectinload(Audit.plant).options(selectinload(Plant.company))
        )

        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        print(from_date, to_date)
        if from_date and to_date:
            stmt = stmt.where(
                Audit.created_at >= from_date, Audit.created_at <= to_date
            )
        elif from_date:
            stmt = stmt.where(Audit.created_at >= from_date)
        elif to_date:
            stmt = stmt.where(Audit.created_at <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, Audit, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, Audit, self.graph)

        result = await self.session.execute(stmt)
        audits = result.scalars().all()

        response = [
            AuditResponse(
                id=audit.id,
                ref=audit.ref,
                type=audit.type,
                standard=audit.standard,
                schedule=audit.schedule,
                start_date=audit.start_date,
                end_date=audit.end_date,
                remarks=audit.remarks,
                plant_id=audit.plant_id,
                plant=PlantResponse(
                    id=audit.plant_id,
                    name=audit.plant.name,
                    code=audit.plant.code,
                    company_id=audit.plant.company_id,
                    company=CompanyResponse(
                        id=audit.plant.company_id,
                        name=audit.plant.company.name,
                        code=audit.plant.company.code,
                        plants=[],
                    ),
                    departments=[],
                ),
            )
            for audit in audits
        ]

        return response
    
    
    async def get_all_audit_ids(self, filters: Optional[str] = None, sort: Optional[str] = None, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None):
        stmt = select(Audit).options(
            selectinload(Audit.plant).options(selectinload(Plant.company))
            
        )
        
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        print(from_date, to_date)
        if from_date and to_date:
            stmt = stmt.where(
                Audit.created_at >= from_date, Audit.created_at <= to_date
            )
        elif from_date:
            stmt = stmt.where(Audit.created_at >= from_date)
        elif to_date:
            stmt = stmt.where(Audit.created_at <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, Audit, self.graph)
            
        if sort:
            stmt = apply_sort(stmt, sort, Audit, self.graph)
            
        result = await self.session.execute(stmt)
        audits = result.scalars().all()
        return [
            {
                "id": audit.id,
                "ref": audit.ref,
            }
            for audit in audits
        ]

    async def get_audit_by_id(self, audit_id: UUID):
        audit = await self.session.execute(
            select(Audit)
            .where(Audit.id == audit_id)
            .options(
                selectinload(Audit.plant).options(
                    selectinload(Plant.company), selectinload(Plant.department)
                )
            )
        )
        audit = audit.scalar_one_or_none()
        if not audit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return AuditResponse(
            id=audit.id,
            ref=audit.ref,
            type=audit.type,
            standard=audit.standard,
            schedule=audit.schedule,
            start_date=audit.start_date,
            end_date=audit.end_date,
            remarks=audit.remarks,
            plant_id=audit.plant_id,
            plant=PlantResponse(
                id=audit.plant_id,
                name=audit.plant.name,
                code=audit.plant.code,
                company_id=audit.plant.company_id,
                company=CompanyResponse(
                    id=audit.plant.company_id,
                    name=audit.plant.company.name,
                    code=audit.plant.company.code,
                    plants=[],
                ),
                departments=[
                    DepartmentResponse(
                        id=department.department_id,
                        name=department.department.name,
                        code=department.department.code,
                        slug=department.department.slug,
                    )
                    for department in audit.plant.departments
                ],
            ),
        )

    async def update_audit(self, audit_id: UUID, data: AuditUpdateRequest):
        audit = await self.session.execute(select(Audit).where(Audit.id == audit_id))
        audit = audit.scalar_one_or_none()

        if not audit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        if audit.type and audit.type != data.type:
            audit.type = data.type
        if audit.standard and audit.standard != data.standard:
            audit.standard = data.standard
        if audit.schedule and audit.schedule != data.schedule:
            audit.schedule = data.schedule
        if audit.start_date and audit.start_date != to_naive(data.start_date):
            audit.start_date = to_naive(data.start_date)
        if audit.end_date and audit.end_date != to_naive(data.end_date):
            audit.end_date = to_naive(data.end_date)
          
        if audit.remarks and audit.remarks != data.remarks:
            audit.remarks = data.remarks
        await self.session.commit()
        return audit

    async def delete_audit(self, audit_id: UUID):
        audit = await self.session.execute(select(Audit).where(Audit.id == audit_id))
        audit = audit.scalar_one_or_none()

        if not audit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(audit)
        await self.session.commit()

    async def create_audit_schedule(self, data: AuditSettingsRequest):
        add_audit_schedule = AuditSchedule(
            name=data.name,
        )
        self.session.add(add_audit_schedule)
        await self.session.commit()
        return add_audit_schedule

    async def get_all_audit_schedules(self):
        audit_schedules = await self.session.execute(select(AuditSchedule))
        audit_schedules = audit_schedules.scalars().all()
        return audit_schedules

    async def get_audit_schedule_by_id(self, audit_schedule_id: UUID):
        audit_schedule = await self.session.execute(
            select(AuditSchedule).where(AuditSchedule.id == audit_schedule_id)
        )
        audit_schedule = audit_schedule.scalar_one_or_none()
        if not audit_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit schedule not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return audit_schedule

    async def update_audit_schedule(
        self, audit_schedule_id: UUID, data: AuditSettingsRequest
    ):
        audit_schedule = await self.session.execute(
            select(AuditSchedule).where(AuditSchedule.id == audit_schedule_id)
        )
        audit_schedule = audit_schedule.scalar_one_or_none()

        if not audit_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit schedule not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        audit_schedule.name = data.name
        await self.session.commit()
        return audit_schedule

    async def delete_audit_schedule(self, audit_schedule_id: UUID):
        audit_schedule = await self.session.execute(
            select(AuditSchedule).where(AuditSchedule.id == audit_schedule_id)
        )
        audit_schedule = audit_schedule.scalar_one_or_none()

        if not audit_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit schedule not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(audit_schedule)
        await self.session.commit()
        return audit_schedule

    async def create_audit_type(self, data: AuditTypeRequest):
        add_audit_type = AuditType(
            name=data.name,
            code=data.code,
        )
        self.session.add(add_audit_type)
        await self.session.commit()
        return add_audit_type

    async def get_all_audit_types(self):
        audit_types = await self.session.execute(select(AuditType))
        audit_types = audit_types.scalars().all()
        return audit_types

    async def get_audit_type_by_id(self, audit_type_id: UUID):
        audit_type = await self.session.execute(
            select(AuditType).where(AuditType.id == audit_type_id)
        )
        audit_type = audit_type.scalar_one_or_none()
        if not audit_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit type not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return audit_type

    async def update_audit_type(self, audit_type_id: UUID, data: AuditTypeRequest):
        audit_type = await self.session.execute(
            select(AuditType).where(AuditType.id == audit_type_id)
        )
        audit_type = audit_type.scalar_one_or_none()

        if not audit_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit type not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        audit_type.name = data.name
        audit_type.code = data.code
        await self.session.commit()
        return audit_type

    async def delete_audit_type(self, audit_type_id: UUID):
        audit_type = await self.session.execute(
            select(AuditType).where(AuditType.id == audit_type_id)
        )
        audit_type = audit_type.scalar_one_or_none()

        if not audit_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit type not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(audit_type)
        await self.session.commit()
        return audit_type

    async def create_audit_standard(self, data: AuditSettingsRequest):
        add_audit_standard = AuditStandard(
            name=data.name,
        )
        self.session.add(add_audit_standard)
        await self.session.commit()
        return add_audit_standard

    async def get_all_audit_standards(self):
        audit_standards = await self.session.execute(select(AuditStandard))
        audit_standards = audit_standards.scalars().all()
        return audit_standards

    async def get_audit_standard_by_id(self, audit_standard_id: UUID):
        audit_standard = await self.session.execute(
            select(AuditStandard).where(AuditStandard.id == audit_standard_id)
        )
        audit_standard = audit_standard.scalar_one_or_none()
        if not audit_standard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit standard not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return audit_standard

    async def update_audit_standard(
        self, audit_standard_id: UUID, data: AuditSettingsRequest
    ):
        audit_standard = await self.session.execute(
            select(AuditStandard).where(AuditStandard.id == audit_standard_id)
        )
        audit_standard = audit_standard.scalar_one_or_none()

        if not audit_standard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit standard not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        audit_standard.name = data.name
        await self.session.commit()
        return audit_standard

    async def delete_audit_standard(self, audit_standard_id: UUID):
        audit_standard = await self.session.execute(
            select(AuditStandard).where(AuditStandard.id == audit_standard_id)
        )
        audit_standard = audit_standard.scalar_one_or_none()

        if not audit_standard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit standard not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(audit_standard)
        await self.session.commit()
        return audit_standard


    async def get_ncr_status_report(
        self,
        audit_id: UUID,
    ):
        now = datetime.now()

        audit = await self.session.execute(select(Audit).where(Audit.id == audit_id))
        audit = audit.scalar_one_or_none()
        if not audit:
            raise HTTPException(status_code=404, detail={
                "message": "Audit not found",
                "success": False,
                "status": status.HTTP_404_NOT_FOUND,
                "data": None,
            })

        audit_info_ids = await self.session.execute(
            select(AuditInfo.id).where(AuditInfo.audit_id == audit_id)
        )
        audit_info_ids = audit_info_ids.scalars().all()

        if not audit_info_ids:
            return {
                "audit_ref": audit.ref,
                "date": now.strftime("%d/%m/%Y"),
                "total_ncrs": 0,
                "closed": {
                    "within_edc": {"count": 0, "references": []},
                    "out_off_edc": {"count": 0, "references": []}
                },
                "pending": {
                    "mr_closer": {"count": 0, "references": []},
                    "followup_audit_delay": {"count": 0, "references": []},
                    "auditee_delay": {
                        "valid_edc": {"count": 0, "references": []},
                        "edc_expire": {"count": 0, "references": []},
                        "no_edc": {"count": 0, "references": []}
                    }
                },
                "rejected": {"count": 0, "references": []}
            }


        ncrs = await self.session.execute(
            select(NCR).where(NCR.audit_info_id.in_(audit_info_ids))
        )
        ncrs = ncrs.scalars().all()

        within_edc = []
        out_of_edc = []
        mr_closer = []
        valid_edc = []
        edc_expire = []
        no_edc = []
        rejected = []
        within_edc_refs = []
        out_of_edc_refs = []
        mr_closer_refs = []
        valid_edc_refs = []
        edc_expire_refs = []
        no_edc_refs = []
        rejected_refs = []

        for n in ncrs:
            # ----- CLOSED -----
            if n.closed_on:
                if n.expected_date_of_completion and n.closed_on <= n.expected_date_of_completion:
                    within_edc.append(n)
                    within_edc_refs.append({
                        "ref": n.ref,
                        "closed_on": n.closed_on.strftime("%Y-%m-%d") if n.closed_on else None,
                        "expected_date_of_completion": n.expected_date_of_completion.strftime("%Y-%m-%d") if n.expected_date_of_completion else None,
                        "rule": "closed_on <= expected_date_of_completion"
                    })
                else:
                    out_of_edc.append(n)
                    out_of_edc_refs.append({
                        "ref": n.ref,
                        "closed_on": n.closed_on.strftime("%Y-%m-%d") if n.closed_on else None,
                        "expected_date_of_completion": n.expected_date_of_completion.strftime("%Y-%m-%d") if n.expected_date_of_completion else None,
                        "rule": "closed_on > expected_date_of_completion"
                    })

            # ----- MR CLOSER -----
            if n.status == NCRStatus.CLOSED:
                mr_closer.append(n)
                mr_closer_refs.append({
                    "ref": n.ref,
                    "status": n.status.value if hasattr(n.status, "value") else str(n.status),
                    "rule": "status = CLOSED (MR close pending)"
                })

            # ----- PENDING -----
            if not n.closed_on:
                if n.expected_date_of_completion:
                    if n.expected_date_of_completion >= now:
                        valid_edc.append(n)
                        valid_edc_refs.append({
                            "ref": n.ref,
                            "expected_date_of_completion": n.expected_date_of_completion.strftime("%Y-%m-%d"),
                            "today": now.strftime("%Y-%m-%d"),
                            "rule": "expected_date_of_completion > today AND closed_on IS NULL"
                        })
                    else:
                        edc_expire.append(n)
                        edc_expire_refs.append({
                            "ref": n.ref,
                            "expected_date_of_completion": n.expected_date_of_completion.strftime("%Y-%m-%d"),
                            "today": now.strftime("%Y-%m-%d"),
                            "rule": "expected_date_of_completion < today AND closed_on IS NULL"
                        })
                else:
                    no_edc.append(n)
                    no_edc_refs.append({
                        "ref": n.ref,
                        "expected_date_of_completion": None,
                        "rule": "expected_date_of_completion IS NULL AND closed_on IS NULL"
                    })

            # ----- REJECTED -----
            if n.rejected_count and n.rejected_count > 0:
                rejected.append(n)
                rejected_refs.append({
                    "ref": n.ref,
                    "rejected_count": n.rejected_count,
                    "rejected_reson": n.rejected_reson,
                    "rule": "rejected_count > 0"
                })

        return {
            "audit_ref": audit.ref,
            "standard": audit.standard,
            "date": now.strftime("%d/%m/%Y"),
            "total_ncrs": len(ncrs),

            "closed": {
                "within_edc": {
                    "count": len(within_edc),
                    "references": within_edc_refs
                },
                "out_off_edc": {
                    "count": len(out_of_edc),
                    "references": out_of_edc_refs
                },
            },

            "pending": {
                "mr_closer": {
                    "count": len(mr_closer),
                    "references": mr_closer_refs
                },
                "followup_audit_delay": {
                    "count": 0,
                    "references": []
                },
                "auditee_delay": {
                    "valid_edc": {
                        "count": len(valid_edc),
                        "references": valid_edc_refs
                    },
                    "edc_expire": {
                        "count": len(edc_expire),
                        "references": edc_expire_refs
                    },
                    "no_edc": {
                        "count": len(no_edc),
                        "references": no_edc_refs
                    }
                }
            },

            "rejected": {
                "count": len(rejected),
                "references": rejected_refs
            }
        }

