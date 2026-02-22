from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from app.audit.models import Audit
from app.audit_info.models import (
    AuditInfo,
    AuditInfoListResponse,
    AuditInfoRequest,
    AuditInfoResponse,
    AuditInfoUpdateRequest,
    AuditTeam,
    AuditTeamRequest,
    AuditTeamResponse,
    AuditTeamRole,
)
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.mail import send_email
from app.ncr.models import NCR, NCRStatus
from app.settings.links import Department
from app.settings.models import Company, DepartmentResponse, Plant
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.suggestions.models import Suggestion
from app.utils.dsl_filter import apply_filters, apply_sort
from app.utils.model_graph import ModelGraph

from app.users.models import UserResponse, User
from app.utils.serializer import to_naive
from app.core.config import settings


class AuditInfoService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build([AuditInfo, AuditTeam, Audit, Department, Plant, Company])

    def _count_ncrs(self, ncrs):
        result = {status.value: 0 for status in NCRStatus}
        for ncr in ncrs:
            status = ncr.status  
            if status in result:
                result[status] += 1
            else:
                result[status] = 1 
        return result

    async def create_audit_info(
        self, data: AuditInfoRequest, background_tasks: BackgroundTasks,user_id: UUID
    ):

        audit = await self.session.execute(
            select(Audit).where(Audit.id == data.audit_id)
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

        department = await self.session.execute(
            select(Department).where(Department.id == data.department_id)
        )
        department = department.scalar_one_or_none()
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Department not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        ref = f"{audit.ref}/{department.code}"

        audit_info = await self.session.execute(
            select(AuditInfo).where(AuditInfo.ref == ref)
        )
        audit_info = audit_info.scalar_one_or_none()
        # if audit_info:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail={
        #             "message": f"You cannot assign team to an department that is already assigned to an audit under the same reference ({audit.ref})",
        #             "success": False,
        #             "status": status.HTTP_404_NOT_FOUND,
        #             "data": None,
        #         },
        #     )

        # if audit.end_date < to_naive(data.from_date):
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail={
        #             "message": "You cannot assign team to an audit that has ended",
        #             "success": False,
        #             "status": status.HTTP_400_BAD_REQUEST,
        #             "data": None,
        #         },
        #     )

        # if audit.start_date < to_naive(data.from_date):
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail={
        #             "message": "You cannot assign team to an audit that has started before the start date",
        #             "success": False,
        #             "status": status.HTTP_400_BAD_REQUEST,
        #             "data": None,
        #         },
        #     )

        # if audit.start_date < to_naive(data.from_date):
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail={
        #             "message": "You cannot assign team to an audit that has started before the start date",
        #             "success": False,
        #             "status": status.HTTP_400_BAD_REQUEST,
        #             "data": None,
        #         },
        #     )

        # if audit.end_date < to_naive(data.from_date):
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail={
        #             "message": "You cannot assign team to an audit that has ended before the start date",
        #             "success": False,
        #             "status": status.HTTP_400_BAD_REQUEST,
        #             "data": None,
        #         },
        #     )
            
        department = await self.session.execute(
            select(Department).where(Department.id == data.department_id)
        )
        department = department.scalar_one_or_none()
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Department not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        add_audit_info = AuditInfo(
            ref=ref,
            department_id=data.department_id,
            from_date=to_naive(data.from_date),
            to_date=to_naive(data.to_date),
            audit_id=data.audit_id,
        )
        self.session.add(add_audit_info)
        await self.session.commit()

        await self.session.refresh(add_audit_info)
        
        
        teams = []
        
        auditee = 'N/A'
        auditor = 'N/A'
                
        for team in data.team:
            user = await self.session.execute(
                select(User).where(User.id == team.user_id)
            )
            user = user.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "User not found",
                        "success": False,
                        "status": status.HTTP_404_NOT_FOUND,
                        "data": None,
                    },
                )

            add_team = AuditTeam(
                user_id=team.user_id,
                role=team.role,
                audit_info_id=add_audit_info.id,
            )
            if team.role == AuditTeamRole.AUDITOR and auditor == 'N/A':
                auditor = user.name
                
            if team.role == AuditTeamRole.AUDITEE:
                auditee = user.name
            self.session.add(add_team)

            await self.session.commit()

            if team.role != AuditTeamRole.AUDITEE:
                

                background_tasks.add_task(
                    send_email,
                    [user.email],
                    "ARe-Audit Management : Audit Assigned",
                    {
                        "user": user.name,
                        "message": (
                            f"<p>This is to inform you that you have been assigned as an internal auditor to conduct the QMS Internal Audit as per the audit schedule.</p>"
                            f"<p><strong>Internal audit Ref. No:</strong> {ref}</p>"
                            f"<p><strong>Date:</strong> {datetime.now().strftime('%d %B %Y')}</p>"
                            f"<p><strong>Audit Date:</strong> {data.from_date.strftime('%d %B %Y')} to {data.to_date.strftime('%d %B %Y')}</p>"
                            f"<p><strong>Department:</strong> {department.name}</p>"
                            f"<p><strong>Auditee:</strong> {auditee}</p>"
                            f"<p><strong>Note:</strong></p>"
                            f"<ul>"
                            f"<li>Kindly plan and execute the audit within the audit window.</li>"
                            f"<li>Please submit hard copies of duly filled audit reports (Observation sheet, IA checklist).</li>"
                            f"<li>Auditors shall submit 'Close Audit' in AReAMS after entering NCRs if any.</li>"
                            f"<li>For field Audit, refer applicable department matrix in Annexure-D.</li>"
                            f"</ul>"
                            f"<p>For any clarification or support, feel free to contact the QMS department.</p>"
                        ),
                        "frontend_url": settings.FRONTEND_URL,
                    },
                )
            else:
                background_tasks.add_task(
                    send_email,
                    [user.email],
                    "ARe-Audit Management : Audit Assigned",
                    {
                        "user": user.name,
                        "message": (
                            f"<p>This is to inform you that you have been assigned as an auditee</p>"
                            f"<p><strong>Internal audit Ref. No:</strong> {ref}</p>"
                            f"<p><strong>Date:</strong> {datetime.now().strftime('%d %B %Y')}</p>"
                            f"<p><strong>Audit Date:</strong> {data.from_date.strftime('%d %B %Y')} to {data.to_date.strftime('%d %B %Y')}</p>"
                            f"<p><strong>Auditor:</strong> {auditor}</p>"
                            f"<p><strong>Department:</strong> {department.name}</p>"
                            f"<p>For any clarification or support, feel free to contact the QMS department.</p>"
                        ),
                        "frontend_url": settings.FRONTEND_URL,
                    },
                )
                
        add_hod = AuditTeam(
            user_id=user_id,
            role=AuditTeamRole.HOD,
            audit_info_id=add_audit_info.id,
        )
        self.session.add(add_hod)
        await self.session.commit()


        return add_audit_info

    async def get_all_audit_info(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(AuditInfo).options(
            selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
            selectinload(AuditInfo.department).options(
                selectinload(Department.plant).options(selectinload(Plant.company))
            ),
            selectinload(AuditInfo.ncrs),
        )
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        if from_date and to_date:
            stmt = stmt.where(
                AuditInfo.from_date >= from_date, AuditInfo.to_date <= to_date
            )
        elif from_date:
            stmt = stmt.where(AuditInfo.from_date >= from_date)
        elif to_date:
            stmt = stmt.where(AuditInfo.to_date <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, AuditInfo, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, AuditInfo, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        audit_infos = result.scalars().all()

        response = AuditInfoListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                AuditInfoResponse(
                    id=audit_info.id,
                    ref=audit_info.ref,
                    department_id=audit_info.department_id,
                    department=DepartmentResponse(
                        id=audit_info.department_id,
                        name=audit_info.department.name,
                        code=audit_info.department.code,
                        slug=audit_info.department.slug,
                    ),
                    from_date=audit_info.from_date,
                    to_date=audit_info.to_date,
                    closed_date=audit_info.closed_date,
                    status=audit_info.status,
                    team=[
                        AuditTeamResponse(
                            id=audit_team.id,
                            user_id=audit_team.user_id,
                            role=audit_team.role,
                            user=UserResponse(
                                id=audit_team.user_id,
                                employee_id=audit_team.user.employee_id,
                                password=audit_team.user.password,
                                email=audit_team.user.email,
                                qualification=audit_team.user.qualification,
                                designation=audit_team.user.designation,
                                is_active=audit_team.user.is_active,
                                role=audit_team.user.role,
                                departments=[],
                                name=audit_team.user.name,
                            ),
                        )
                        for audit_team in audit_info.team
                    ],
                    audit=None,
                    ncr_status_count={
                        **self._count_ncrs(audit_info.ncrs),
                        "total": len(audit_info.ncrs),
                    },
                )
                for audit_info in audit_infos
            ],
        )

        return response

    async def get_audit_info_by_id(self, audit_info_id: UUID):
        audit_info = await self.session.execute(
            select(AuditInfo)
            .where(AuditInfo.id == audit_info_id)
            .options(
                selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
                selectinload(AuditInfo.department).options(
                    selectinload(Department.plant).options(selectinload(Plant.company))
                ),
            )
        )
        audit_info = audit_info.scalar_one_or_none()
        if not audit_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit info not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return AuditInfoResponse(
            id=audit_info.id,
            ref=audit_info.ref,
            department_id=audit_info.department_id,
            department=DepartmentResponse(
                id=audit_info.department_id,
                name=audit_info.department.name,
                code=audit_info.department.code,
                slug=audit_info.department.slug,
            ),
            from_date=audit_info.from_date,
            to_date=audit_info.to_date,
            closed_date=audit_info.closed_date,
            status=audit_info.status,
            team=[
                AuditTeamResponse(
                    id=audit_team.id,
                    user_id=audit_team.user_id,
                    role=audit_team.role,
                    user=UserResponse(
                        id=audit_team.user_id,
                        employee_id=audit_team.user.employee_id,
                        password=audit_team.user.password,
                        email=audit_team.user.email,
                        qualification=audit_team.user.qualification,
                        designation=audit_team.user.designation,
                        is_active=audit_team.user.is_active,
                        role=audit_team.user.role,
                        departments=[],
                        name=audit_team.user.name,
                    ),
                )
                for audit_team in audit_info.team
            ],
            audit=None,
        )

    async def update_audit_info(
        self, audit_info_id: UUID, data: AuditInfoUpdateRequest, user_id: UUID, background_tasks: BackgroundTasks
    ):
        val = data.model_dump(exclude_unset=True)
        ncr_count_subq = await self.session.execute(
            select(func.count(NCR.id))
            .where(NCR.audit_info_id == AuditInfo.id)
            
        )
        
        ncr_count = ncr_count_subq.scalar()
        
        suggestion_count_subq = await self.session.execute(
            select(func.count(Suggestion.id))
            .where(Suggestion.audit_info_id == AuditInfo.id)
           
        )
        suggestion_count = suggestion_count_subq.scalar()
   
        

        audit_info = await self.session.execute(
            select(AuditInfo).where(AuditInfo.id == audit_info_id).options(
                selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
                selectinload(AuditInfo.department),
              
            )
        )
        audit_info = audit_info.scalar_one_or_none()

        if not audit_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit info not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
            
        hod = next(
            (
                team
                for team in audit_info.team
                if team.role == AuditTeamRole.HOD
            ),
            None,
        )
        
        
        auditor = next(
            (member for member in audit_info.team if member.role == AuditTeamRole.AUDITOR),
            None,
        )
        
        auditee = next(
            (member for member in audit_info.team if member.role == AuditTeamRole.AUDITEE),
            None,
        )
      
        if "from_date" in val:
            audit_info.from_date = to_naive(val["from_date"])

        if "to_date" in val:
            audit_info.to_date = to_naive(val["to_date"])

        if "closed_date" in val:
            audit_info.closed_date = to_naive(val["closed_date"])
            audit_info.status = "CLOSED"
            if(user_id == auditor.user.id):
                background_tasks.add_task(
                    send_email,
                    [hod.user.email],
                    f"ARe-Audit Management : Internal Audit Closed - {audit_info.ref}",
                    {
                        "user": hod.user.name,
                        "message": (
                            f"<p>This is to inform you that the auditor has completed the internal audit {audit_info.ref} and closed the same in the AReAMS system.</p>"
                            f"<p><strong>Internal audit Ref. No:</strong> {audit_info.ref}</p>"
                            f"<p><strong>Audit Date:</strong> {audit_info.from_date.strftime('%d %B %Y')} to {audit_info.to_date.strftime('%d %B %Y')}</p>"
                            f"<p><strong>Department:</strong> {audit_info.department.name}</p>"
                            f"<p><strong>Auditor:</strong> {auditor.user.name}</p>"
                            f"<p><strong>Auditee:</strong> {auditee.user.name}</p>"
                            f"<p><strong>No. of NCRs:</strong> {ncr_count}</p>"
                            f"<p><strong>No. of Suggestions:</strong> {suggestion_count}</p>"
                            f"<p>For any clarification or support, please feel free to contact the QMS department.</p>"
                        ),
                        "frontend_url": settings.FRONTEND_URL,
                    },
                )
        await self.session.commit()
        return audit_info

    async def delete_audit_info(self, audit_info_id: UUID):
        audit_info = await self.session.execute(
            select(AuditInfo).where(AuditInfo.id == audit_info_id)
        )
        audit_info = audit_info.scalar_one_or_none()

        if not audit_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit info not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(audit_info)
        await self.session.commit()

    async def export_all_audit_info(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(AuditInfo).options(
            selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
            selectinload(AuditInfo.department).options(
                selectinload(Department.plant).options(selectinload(Plant.company))
            ),
            selectinload(AuditInfo.ncrs),
        )
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        if from_date and to_date:
            stmt = stmt.where(
                AuditInfo.from_date >= from_date, AuditInfo.to_date <= to_date
            )
        elif from_date:
            stmt = stmt.where(AuditInfo.from_date >= from_date)
        elif to_date:
            stmt = stmt.where(AuditInfo.to_date <= to_date)

        if filters:
            print(filters)
            stmt = apply_filters(stmt, filters, AuditInfo, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, AuditInfo, self.graph)

        result = await self.session.execute(stmt)
        audit_infos = result.scalars().all()

        response = [
            AuditInfoResponse(
                id=audit_info.id,
                ref=audit_info.ref,
                department_id=audit_info.department_id,
                department=DepartmentResponse(
                    id=audit_info.department_id,
                    name=audit_info.department.name,
                    code=audit_info.department.code,
                    slug=audit_info.department.slug,
                ),
                from_date=audit_info.from_date,
                to_date=audit_info.to_date,
                closed_date=audit_info.closed_date,
                status=audit_info.status,
                team=[
                    AuditTeamResponse(
                        id=audit_team.id,
                        user_id=audit_team.user_id,
                        role=audit_team.role,
                        user=UserResponse(
                            id=audit_team.user_id,
                            employee_id=audit_team.user.employee_id,
                            password=audit_team.user.password,
                            email=audit_team.user.email,
                            qualification=audit_team.user.qualification,
                            designation=audit_team.user.designation,
                            is_active=audit_team.user.is_active,
                            role=audit_team.user.role,
                            name=audit_team.user.name,
                            departments=[],
                        ),
                    )
                    for audit_team in audit_info.team
                ],
                audit=None,
                ncr_status_count={
                    **self._count_ncrs(audit_info.ncrs),
                    "total": len(audit_info.ncrs),
                },
            )
            for audit_info in audit_infos
        ]

        return response

    async def create_audit_team(
        self,
        data: AuditTeamRequest,
        audit_info_id: UUID,
        background_tasks: BackgroundTasks,
    ):

        audit_info = await self.session.execute(
            select(AuditInfo)
            .where(AuditInfo.id == audit_info_id)
            .options(
                selectinload(AuditInfo.department).options(
                    selectinload(Department.plant).options(selectinload(Plant.company))
                ),
                selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
            )
        )
        audit_info = audit_info.scalar_one_or_none()

        if not audit_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit info not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        is_audit_team = await self.session.execute(
            select(AuditTeam).where(
                AuditTeam.id == data.user_id, AuditTeam.audit_info_id == audit_info_id
            )
        )
        is_audit_team = is_audit_team.scalar_one_or_none()
        if is_audit_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "User already assigned to audit info",
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "data": None,
                },
            )

        user = await self.session.execute(select(User).where(User.id == data.user_id))
        user = user.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        audit_team = AuditTeam(
            user_id=data.user_id,
            role=data.role,
            audit_info_id=audit_info_id,
        )
        self.session.add(audit_team)
        await self.session.commit()

        if data.role != AuditTeamRole.AUDITEE:
            auditee = next(
                (
                    x.user.name
                    for x in audit_info.team
                    if x.role == AuditTeamRole.AUDITEE and x.user
                ),
                "N/A",
            )

            background_tasks.add_task(
                send_email,
                [user.email],
                "ARe-Audit Management : Audit Assigned",
                {
                    "user": user.name,
                    "message": (
                        f"<p>This is to inform you that you have been assigned as an internal auditor to conduct the QMS Internal Audit as per the audit schedule.</p>"
                        f"<p><strong>Internal audit Ref. No:</strong> {audit_info.ref}</p>"
                        f"<p><strong>Date:</strong> {datetime.now().strftime('%d %B %Y')}</p>"
                        f"<p><strong>Audit Date:</strong> {audit_info.from_date.strftime('%d %B %Y')} to {audit_info.to_date.strftime('%d %B %Y')}</p>"
                        f"<p><strong>Department:</strong> {audit_info.department.name}</p>"
                        f"<p><strong>Auditee:</strong> {auditee}</p>"
                        f"<p><strong>Note:</strong></p>"
                        f"<ul>"
                        f"<li>Kindly plan and execute the audit within the audit window.</li>"
                        f"<li>Please submit hard copies of duly filled audit reports (Observation sheet, IA checklist).</li>"
                        f"<li>Auditors shall submit 'Close Audit' in AReAMS after entering NCRs if any.</li>"
                        f"<li>For field Audit, refer applicable department matrix in Annexure-D.</li>"
                        f"</ul>"
                        f"<p>For any clarification or support, feel free to contact the QMS department.</p>"
                    ),
                    "frontend_url": settings.FRONTEND_URL,
                },
            )
        else:
            background_tasks.add_task(
                send_email,
                [user.email],
                "ARe-Audit Management : Audit Assigned",
                {
                    "user": user.name,
                    "message": (
                        f"<p>This is to inform you that you have been assigned as an auditee</p>"
                        f"<p><strong>Internal audit Ref. No:</strong> {audit_info.ref}</p>"
                        f"<p><strong>Date:</strong> {datetime.now().strftime('%d %B %Y')}</p>"
                        f"<p><strong>Audit Date:</strong> {audit_info.from_date.strftime('%d %B %Y')} to {audit_info.to_date.strftime('%d %B %Y')}</p>"
                        f"<p><strong>Department:</strong> {audit_info.department.name}</p>"
                        f"<p>For any clarification or support, feel free to contact the QMS department.</p>"
                    ),
                    "frontend_url": settings.FRONTEND_URL,
                },
            )
        

        return audit_team

    async def remove_audit_team(self, audit_info_id: UUID, id: UUID):
        audit_info = await self.session.execute(
            select(AuditInfo).where(AuditInfo.id == audit_info_id)
        )
        audit_info = audit_info.scalar_one_or_none()

        if not audit_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Audit info not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        is_audit_team = await self.session.execute(
            select(AuditTeam).where(
                AuditTeam.id == id, AuditTeam.audit_info_id == audit_info_id
            )
        )
        is_audit_team = is_audit_team.scalar_one_or_none()
        if not is_audit_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "User not assigned to audit info",
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "data": None,
                },
            )
        await self.session.delete(is_audit_team)
        await self.session.commit()

        return is_audit_team

    async def get_audit_info_by_audit_id(self, audit_id: UUID):
        result = await self.session.execute(
            select(AuditInfo)
            .where(AuditInfo.audit_id == audit_id)
            .options(
                selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
                selectinload(AuditInfo.department).options(
                    selectinload(Department.plant).options(selectinload(Plant.company))
                ),
            )
        )
        audit_infos = result.scalars().all()

        return [
            AuditInfoResponse(
                id=audit_info.id,
                ref=audit_info.ref,
                department_id=audit_info.department_id,
                department=DepartmentResponse(
                    id=audit_info.department_id,
                    name=audit_info.department.name,
                    code=audit_info.department.code,
                    slug=audit_info.department.slug,
                ),
                from_date=audit_info.from_date,
                to_date=audit_info.to_date,
                closed_date=audit_info.closed_date,
                status=audit_info.status,
                team=[
                    AuditTeamResponse(
                        id=audit_team.id,
                        user_id=audit_team.user_id,
                        role=audit_team.role,
                        user=UserResponse(
                            id=audit_team.user_id,
                            employee_id=audit_team.user.employee_id,
                            password=audit_team.user.password,
                            email=audit_team.user.email,
                            qualification=audit_team.user.qualification,
                            designation=audit_team.user.designation,
                            is_active=audit_team.user.is_active,
                            role=audit_team.user.role,
                            departments=[],
                        ),
                    )
                    for audit_team in audit_info.team
                ],
                audit=None,
            )
            for audit_info in audit_infos
        ]
