from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy import func, select
from app.audit.models import Audit
from app.audit_info.models import AuditInfo, AuditTeam
from app.settings.models import Department, Plant
from app.suggestions.models import (
    Suggestion,
    SuggestionCreateRequest,
    SuggestionTeam,
    SuggestionTeamRole,
    SuggestionUpdateRequest,
    SuggestionStatus
)
from typing import Optional
from app.utils.model_graph import ModelGraph
from sqlalchemy.orm import selectinload
from uuid import UUID
from app.utils.dsl_filter import apply_filters, apply_sort
from app.audit.models import AuditResponse
from app.audit_info.models import (
    AuditInfoResponse,
    AuditTeamResponse,
)
from app.settings.models import (
    DepartmentResponse,
    PlantResponse,
    CompanyResponse,
)
from app.suggestions.models import (
    SuggestionResponse,
    SuggestionListResponse,
    SuggestionTeamResponse,
    SuggestionTeamCreateRequest,
)
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.users.models import User, UserResponse
from app.utils.serializer import to_naive


class SuggestionService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build(
            [
                Suggestion,
                SuggestionTeam,
                AuditInfo,
                AuditTeam,
                Audit,
                Plant,
                Department,
            ]
        )

    async def create_suggestion(self, data: SuggestionCreateRequest, user_id: UUID):
        audit_info = await self.session.execute(
            select(AuditInfo)
            .where(AuditInfo.id == data.audit_info_id)
            .options(selectinload(AuditInfo.department))
            .options(selectinload(AuditInfo.team))
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
        suggestion_count = await self.session.execute(select(func.count(Suggestion.id)))
        suggestion_count = suggestion_count.scalar()
        year = f"{datetime.now().year}-{datetime.now().year + 1}"
        ref = f"Sug/{suggestion_count + 1}/{year}/{audit_info.department.slug}"

        suggestion = Suggestion(
            ref=ref,
            audit_info_id=data.audit_info_id,
            suggestion=data.suggestion,
        )

        self.session.add(suggestion)
        await self.session.commit()

        suggestion_team = SuggestionTeam(
            user_id=user_id,
            role=SuggestionTeamRole.CREATED_BY,
            suggestion_id=suggestion.id,
        )

        self.session.add(suggestion_team)
        await self.session.commit()
        auditee_member = next(
            (
                member
                for member in audit_info.team
                if member.role == SuggestionTeamRole.AUDITEE
            ),
            None,
        )
        auditee = SuggestionTeam(
            user_id=auditee_member.user_id,
            role=SuggestionTeamRole.AUDITEE,
            suggestion_id=suggestion.id,
        )

        self.session.add(auditee)
        await self.session.commit()

        return suggestion

    async def update_suggestion(
        self, suggestion_id: UUID, data: SuggestionUpdateRequest
    ):
        suggestion = await self.session.execute(
            select(Suggestion).where(Suggestion.id == suggestion_id)
        )
        suggestion = suggestion.scalar_one_or_none()
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Suggestion not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        if data.audit_info_id:
            audit_info = await self.session.execute(
                select(AuditInfo)
                .where(AuditInfo.id == data.audit_info_id)
                .options(selectinload(AuditInfo.department))
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
            suggestion.audit_info_id = data.audit_info_id
            suggestion.audit_info = audit_info
        if data.suggestion:
            suggestion.suggestion = data.suggestion
        if data.corrective_action:
            suggestion.corrective_action = data.corrective_action
        if data.status:

            if data.status == SuggestionStatus.CLOSED:
                suggestion.actual_date_of_completion = to_naive(datetime.now())
            suggestion.status = data.status

        if data.expected_date_of_completion:
            suggestion.expected_date_of_completion = to_naive(data.expected_date_of_completion)
        if data.actual_date_of_completion:
            suggestion.actual_date_of_completion = to_naive(data.actual_date_of_completion)
        await self.session.commit()
        return suggestion
    
    
    async def delete_suggestion(self, suggestion_id: UUID):
        suggestion = await self.session.execute(
            select(Suggestion).where(Suggestion.id == suggestion_id)
        )
        suggestion = suggestion.scalar_one_or_none()
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Suggestion not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(suggestion)
        await self.session.commit()
        return suggestion
    
    

    async def get_all_suggestions(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        stmt = select(Suggestion).options(
            selectinload(Suggestion.audit_info).options(
                selectinload(AuditInfo.department),
                selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
                   selectinload(AuditInfo.audit).options(
            selectinload(Audit.plant).options(
                selectinload(Plant.company)
            )
        ),
            ),
            
            selectinload(Suggestion.team).options(selectinload(SuggestionTeam.user)),
        )
        if from_date:
            from_date = to_naive(from_date)
            stmt = stmt.where(Suggestion.created_at >= to_naive(from_date))
        if to_date:
            to_date = to_naive(to_date)
            stmt = stmt.where(Suggestion.created_at <= to_naive(to_date))
        if filters:
            stmt = apply_filters(stmt, filters, Suggestion, self.graph)
        if sort:
            stmt = apply_sort(stmt, sort, Suggestion, self.graph)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size).distinct()
        result = await self.session.execute(stmt)
        suggestions = result.scalars().all()
        response = SuggestionListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                SuggestionResponse(
                    id=suggestion.id,
                    ref=suggestion.ref,
                    created_at = suggestion.created_at,
                    status=suggestion.status,
                    audit_info_id=suggestion.audit_info_id,
                    expected_date_of_completion=suggestion.expected_date_of_completion,
                    actual_date_of_completion=suggestion.actual_date_of_completion,
                    suggestion=suggestion.suggestion,
                    corrective_action=suggestion.corrective_action,
                    audit_info=AuditInfoResponse(
                        id=suggestion.audit_info_id,
                        ref=suggestion.audit_info.ref,
                        department_id=suggestion.audit_info.department_id,
                        department=DepartmentResponse(
                            id=suggestion.audit_info.department.id,
                            name=suggestion.audit_info.department.name,
                            code=suggestion.audit_info.department.code,
                            created_at=suggestion.audit_info.department.created_at,
                            updated_at=suggestion.audit_info.department.updated_at,
                            slug=suggestion.audit_info.department.slug,
                        ),
                        from_date=suggestion.audit_info.from_date,
                        to_date=suggestion.audit_info.to_date,
                        closed_date=suggestion.audit_info.closed_date,
                        status=suggestion.audit_info.status,
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
                            for audit_team in suggestion.audit_info.team
                        ],
                        audit=AuditResponse(
                            id=suggestion.audit_info.audit.id,
                            ref=suggestion.audit_info.audit.ref,
                            type=suggestion.audit_info.audit.type,
                            schedule=suggestion.audit_info.audit.schedule,
                            created_at=suggestion.audit_info.audit.created_at,
                            updated_at=suggestion.audit_info.audit.updated_at,
                            standard=suggestion.audit_info.audit.standard,
                            start_date=suggestion.audit_info.audit.start_date,
                            end_date=suggestion.audit_info.audit.end_date,
                            plant=PlantResponse(
                                id=suggestion.audit_info.audit.plant.id,
                                name=suggestion.audit_info.audit.plant.name,
                                code=suggestion.audit_info.audit.plant.code,
                                created_at=suggestion.audit_info.audit.plant.created_at,
                                updated_at=suggestion.audit_info.audit.plant.updated_at,
                                company_id=suggestion.audit_info.audit.plant.company.id,
                                company=CompanyResponse(
                                    id=suggestion.audit_info.audit.plant.company.id,
                                    name=suggestion.audit_info.audit.plant.company.name,
                                    code=suggestion.audit_info.audit.plant.company.code,
                                    created_at=suggestion.audit_info.audit.plant.company.created_at,
                                    updated_at=suggestion.audit_info.audit.plant.company.updated_at,
                                ),
                            ),
                            plant_id=suggestion.audit_info.audit.plant.id,
                        ),
                    ),
                    team=[
                        SuggestionTeamResponse(
                            id=suggestion_team.id,
                            user_id=suggestion_team.user_id,
                            role=suggestion_team.role,
                            ncr_id=suggestion_team.suggestion_id,
                            user=UserResponse(
                                id=suggestion_team.user_id,
                                employee_id=suggestion_team.user.employee_id,
                                password=suggestion_team.user.password,
                                email=suggestion_team.user.email,
                                qualification=suggestion_team.user.qualification,
                                designation=suggestion_team.user.designation,
                                is_active=suggestion_team.user.is_active,
                                role=suggestion_team.user.role,
                                departments=[],
                                name=suggestion_team.user.name,
                            ),
                        )
                        for suggestion_team in suggestion.team
                    ],
                )
                for suggestion in suggestions
            ],
        )
        return response
    
    async def export_all_suggestions(
            self,
            filters: Optional[str] = None,
            sort: Optional[str] = None,
            from_date: Optional[datetime] = None,
            to_date: Optional[datetime] = None,
        ):
            stmt = select(Suggestion).options(
                selectinload(Suggestion.audit_info).options(
                    selectinload(AuditInfo.department),
                    selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
                    selectinload(AuditInfo.audit).options(
                selectinload(Audit.plant).options(
                    selectinload(Plant.company)
                )
            ),
                ),
                
                selectinload(Suggestion.team).options(selectinload(SuggestionTeam.user)),
            )
            if from_date:
                from_date = to_naive(from_date)
                stmt = stmt.where(Suggestion.created_at >= to_naive(from_date))
            if to_date:
                to_date = to_naive(to_date)
                stmt = stmt.where(Suggestion.created_at <= to_naive(to_date))
            if filters:
                stmt = apply_filters(stmt, filters, Suggestion, self.graph)
            if sort:
                stmt = apply_sort(stmt, sort, Suggestion, self.graph)
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await self.session.execute(count_stmt).distinct()
            total = total_result.scalar()
            result = await self.session.execute(stmt)
            suggestions = result.scalars().all()
            response = [
                    SuggestionResponse(
                        id=suggestion.id,
                        ref=suggestion.ref,
                        created_at = suggestion.created_at,
                        status=suggestion.status,
                        audit_info_id=suggestion.audit_info_id,
                        expected_date_of_completion=suggestion.expected_date_of_completion,
                        actual_date_of_completion=suggestion.actual_date_of_completion,
                        suggestion=suggestion.suggestion,
                        corrective_action=suggestion.corrective_action,
                        audit_info=AuditInfoResponse(
                            id=suggestion.audit_info_id,
                            ref=suggestion.audit_info.ref,
                            department_id=suggestion.audit_info.department_id,
                            department=DepartmentResponse(
                                id=suggestion.audit_info.department.id,
                                name=suggestion.audit_info.department.name,
                                code=suggestion.audit_info.department.code,
                                created_at=suggestion.audit_info.department.created_at,
                                updated_at=suggestion.audit_info.department.updated_at,
                                slug=suggestion.audit_info.department.slug,
                            ),
                            from_date=suggestion.audit_info.from_date,
                            to_date=suggestion.audit_info.to_date,
                            closed_date=suggestion.audit_info.closed_date,
                            status=suggestion.audit_info.status,
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
                                for audit_team in suggestion.audit_info.team
                            ],
                            audit=AuditResponse(
                                id=suggestion.audit_info.audit.id,
                                ref=suggestion.audit_info.audit.ref,
                                type=suggestion.audit_info.audit.type,
                                schedule=suggestion.audit_info.audit.schedule,
                                created_at=suggestion.audit_info.audit.created_at,
                                updated_at=suggestion.audit_info.audit.updated_at,
                                standard=suggestion.audit_info.audit.standard,
                                start_date=suggestion.audit_info.audit.start_date,
                                end_date=suggestion.audit_info.audit.end_date,
                                plant=PlantResponse(
                                    id=suggestion.audit_info.audit.plant.id,
                                    name=suggestion.audit_info.audit.plant.name,
                                    code=suggestion.audit_info.audit.plant.code,
                                    created_at=suggestion.audit_info.audit.plant.created_at,
                                    updated_at=suggestion.audit_info.audit.plant.updated_at,
                                    company_id=suggestion.audit_info.audit.plant.company.id,
                                    company=CompanyResponse(
                                        id=suggestion.audit_info.audit.plant.company.id,
                                        name=suggestion.audit_info.audit.plant.company.name,
                                        code=suggestion.audit_info.audit.plant.company.code,
                                        created_at=suggestion.audit_info.audit.plant.company.created_at,
                                        updated_at=suggestion.audit_info.audit.plant.company.updated_at,
                                    ),
                                ),
                                plant_id=suggestion.audit_info.audit.plant.id,
                            ),
                        ),
                        team=[
                            SuggestionTeamResponse(
                                id=suggestion_team.id,
                                user_id=suggestion_team.user_id,
                                role=suggestion_team.role,
                                ncr_id=suggestion_team.suggestion_id,
                                user=UserResponse(
                                    id=suggestion_team.user_id,
                                    employee_id=suggestion_team.user.employee_id,
                                    password=suggestion_team.user.password,
                                    email=suggestion_team.user.email,
                                    qualification=suggestion_team.user.qualification,
                                    designation=suggestion_team.user.designation,
                                    is_active=suggestion_team.user.is_active,
                                    role=suggestion_team.user.role,
                                    departments=[],
                                    name=suggestion_team.user.name,
                                ),
                            )
                            for suggestion_team in suggestion.team
                        ],
                    )
                    for suggestion in suggestions
                ]
            
            return response
        
    async def add_suggestion_team(
        self, team: SuggestionTeamCreateRequest
    ):
        suggestion = await self.session.execute(
            select(Suggestion).where(Suggestion.id == team.suggestion_id)
        )
        suggestion = suggestion.scalar_one_or_none()

        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Suggestion not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        suggestion_team = SuggestionTeam(
            user_id=team.user_id,
            role=team.role,
            suggestion_id=team.suggestion_id,
        )
        self.session.add(suggestion_team)
        await self.session.commit()
        return suggestion_team

    async def delete_suggestion_team(self, team_id: UUID):
        suggestion_team = await self.session.execute(
            select(SuggestionTeam).where(SuggestionTeam.id == team_id)
        )
        suggestion_team = suggestion_team.scalar_one_or_none()

        if not suggestion_team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Suggestion team not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(suggestion_team)
        await self.session.commit()
        check = await self.session.execute(
            select(SuggestionTeam).where(SuggestionTeam.id == team_id)
        )
        print("TEAM AFTER DELETE:", check.scalar_one_or_none())
        return suggestion_team
