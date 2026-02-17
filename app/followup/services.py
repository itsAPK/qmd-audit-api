from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from app.audit.models import Audit, AuditResponse
from app.audit_info.models import (
    AuditInfo,
    AuditInfoResponse,
    AuditTeam,
    AuditTeamResponse,
)
from app.followup.models import (
    CreateFollowupRequest,
    Followup,
    FollowupListResponse,
    FollowupResponse,
    FollowupStatus,
    UpdateFollowupRequest,
)
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.ncr.models import (
    NCR,
    DocumentReference,
    NCRFiles,
    NCRResponse,
    NCRStatus,
    NCRTeam,
    NCRTeamResponse,
    NCRTeamRole,
)
from app.settings.models import Department, DepartmentResponse, Plant
from app.users.models import UserResponse
from app.utils.dsl_filter import apply_filters, apply_sort
from app.utils.model_graph import ModelGraph
from app.utils.serializer import to_naive


class FollowupService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build(
            [
                Followup,
                NCR,
                AuditInfo,
                AuditTeam,
                NCRTeam,
                DocumentReference,
                NCRFiles,
                Audit,
                Department,
                Plant,
            ]
        )

    async def create_followup(self, data: CreateFollowupRequest, user_id: UUID):
        ncr = await self.session.execute(select(NCR).where(NCR.id == data.ncr_id))
        ncr = ncr.scalar_one_or_none()
        if not ncr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "NCR not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        followup = Followup(
            ncr_id=data.ncr_id,
            requested_by_id=user_id,
            requested_date=datetime.now(),
        )
        self.session.add(followup)

        ncr.status = NCRStatus.FOLLOWUP_REQUESTED

        await self.session.commit()
        return followup

    async def update_followup(self, followup_id: UUID, data: UpdateFollowupRequest):
        followup = await self.session.execute(
            select(Followup).where(Followup.id == followup_id)
        )
        followup = followup.scalar_one_or_none()

        ncr = await self.session.execute(select(NCR).where(NCR.id == followup.ncr_id))

        ncr = ncr.scalar_one_or_none()

        if not followup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Followup not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        if data.auditor_id:
            followup.auditor_id = data.auditor_id
            followup.status = FollowupStatus.ASSIGNED
            ncr.status = NCRStatus.FOLLOW_ASSIGNED
            followup.assgined_on = datetime.now()
            
            update_ncr_team = NCRTeam(
                user_id=data.auditor_id,
                role=NCRTeamRole.FOLLOWUP_AUDITOR,
                ncr_id=followup.ncr_id,
            )
            self.session.add(update_ncr_team)
            await self.session.commit()

        if data.observations:
            followup.observations = data.observations
            ncr.followup_observations = data.observations
            followup.completed_on = to_naive(datetime.now())
            followup.status = FollowupStatus.COMPLETED
            ncr.actual_date_of_completion = datetime.now()
            ncr.status = NCRStatus.FOLLOW_COMPLETED
            ncr.followup_date = to_naive(datetime.now())

        if data.completed_on:
            followup.completed_on = to_naive(data.completed_on)
            ncr.followup_date = to_naive(datetime.now())
        await self.session.commit()
        return followup

    async def get_all_followups(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        stmt = select(Followup).options(
            selectinload(Followup.ncr).options(
                selectinload(NCR.team).options(selectinload(NCRTeam.user)),
                selectinload(NCR.audit_info).options(
                    selectinload(AuditInfo.audit), selectinload(AuditInfo.department)
                ),
            ),
            selectinload(Followup.auditor),
            selectinload(Followup.requested_by),
        )

        if filters:
            stmt = apply_filters(stmt, filters, Followup, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, Followup, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        followups = result.scalars().all()

        response = FollowupListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                FollowupResponse(
                    id=followup.id,
                    requested_date=followup.requested_date,
                    status=followup.status,
                    ncr_id=followup.ncr_id,
                    auditor_id=followup.auditor_id,
                    observations=followup.observations,
                    auditor=(
                        UserResponse(
                            id=followup.auditor.id,
                            employee_id=followup.auditor.employee_id,
                            name=followup.auditor.name,
                        )
                        if followup.auditor
                        else None
                    ),
                    requested_by_id=followup.requested_by_id,
                    assgined_on=followup.assgined_on,
                    completed_on=followup.completed_on,
                    requested_by=UserResponse(
                        id=followup.requested_by.id,
                        employee_id=followup.requested_by.employee_id,
                        name=followup.requested_by.name,
                    ),
                    ncr=NCRResponse(
                        id=followup.ncr_id,
                        ref=followup.ncr.ref,
                        repeat=followup.ncr.repeat,
                        status=followup.ncr.status,
                        mode=followup.ncr.mode,
                        shift=followup.ncr.shift,
                        type=followup.ncr.type,
                        audit_info_id=followup.ncr.audit_info_id,
                        description=followup.ncr.description,
                        objective_evidence=followup.ncr.objective_evidence,
                        requirement=followup.ncr.requirement,
                        main_clause=followup.ncr.main_clause,
                        sub_clause=followup.ncr.sub_clause,
                        ss_clause=followup.ncr.ss_clause,
                        correction=followup.ncr.correction,
                        root_cause=followup.ncr.root_cause,
                        systematic_corrective_action=followup.ncr.systematic_corrective_action,
                        corrective_action_details=followup.ncr.corrective_action_details,
                        expected_date_of_completion=followup.ncr.expected_date_of_completion,
                        actual_date_of_completion=followup.ncr.actual_date_of_completion,
                        edc_given_date=followup.ncr.edc_given_date,
                        remarks=followup.ncr.remarks,
                        followup_observations=followup.ncr.followup_observations,
                        followup_date=followup.ncr.followup_date,
                        rejected_reson=followup.ncr.rejected_reson,
                        rejected_count=followup.ncr.rejected_count,
                        closed_on=followup.ncr.closed_on,
                        files=[],
                        document_references=[],
                        team=[
                            NCRTeamResponse(
                                id=ncr_team.id,
                                user_id=ncr_team.user_id,
                                role=ncr_team.role,
                                ncr_id=ncr_team.ncr_id,
                                user=UserResponse(
                                    id=ncr_team.user.id,
                                    employee_id=ncr_team.user.employee_id,
                                    name=ncr_team.user.name,
                                ),
                            )
                            for ncr_team in followup.ncr.team
                        ],
                        audit_info=AuditInfoResponse(
                            id=followup.ncr.audit_info_id,
                            ref=followup.ncr.audit_info.ref,
                            department_id=followup.ncr.audit_info.department_id,
                            department=DepartmentResponse(
                                id=followup.ncr.audit_info.department.id,
                                name=followup.ncr.audit_info.department.name,
                                code=followup.ncr.audit_info.department.code,
                                created_at=followup.ncr.audit_info.department.created_at,
                                updated_at=followup.ncr.audit_info.department.updated_at,
                                slug=followup.ncr.audit_info.department.slug,
                            ),
                            from_date=followup.ncr.audit_info.from_date,
                            to_date=followup.ncr.audit_info.to_date,
                            closed_date=followup.ncr.audit_info.closed_date,
                            status=followup.ncr.audit_info.status,
                        ),
                    ),
                    created_at=followup.created_at,
                )
                for followup in followups
            ],
        )

        return response
    async def export_all_followups(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
    
    ):
        stmt = select(Followup).options(
            selectinload(Followup.ncr).options(
                selectinload(NCR.team).options(selectinload(NCRTeam.user)),
                selectinload(NCR.audit_info).options(
                    selectinload(AuditInfo.audit), selectinload(AuditInfo.department)
                ),
            ),
            selectinload(Followup.auditor),
            selectinload(Followup.requested_by),
        )

        if filters:
            stmt = apply_filters(stmt, filters, Followup, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, Followup, self.graph)

     

      
        result = await self.session.execute(stmt)
        followups = result.scalars().all()

        response =[
                FollowupResponse(
                    id=followup.id,
                    requested_date=followup.requested_date,
                    status=followup.status,
                    ncr_id=followup.ncr_id,
                    auditor_id=followup.auditor_id,
                    observations=followup.observations,
                    auditor=(
                        UserResponse(
                            id=followup.auditor.id,
                            employee_id=followup.auditor.employee_id,
                            name=followup.auditor.name,
                        )
                        if followup.auditor
                        else None
                    ),
                    requested_by_id=followup.requested_by_id,
                    assgined_on=followup.assgined_on,
                    completed_on=followup.completed_on,
                    requested_by=UserResponse(
                        id=followup.requested_by.id,
                        employee_id=followup.requested_by.employee_id,
                        name=followup.requested_by.name,
                    ),
                    ncr=NCRResponse(
                        id=followup.ncr_id,
                        ref=followup.ncr.ref,
                        repeat=followup.ncr.repeat,
                        status=followup.ncr.status,
                        mode=followup.ncr.mode,
                        shift=followup.ncr.shift,
                        type=followup.ncr.type,
                        audit_info_id=followup.ncr.audit_info_id,
                        description=followup.ncr.description,
                        objective_evidence=followup.ncr.objective_evidence,
                        requirement=followup.ncr.requirement,
                        main_clause=followup.ncr.main_clause,
                        sub_clause=followup.ncr.sub_clause,
                        ss_clause=followup.ncr.ss_clause,
                        correction=followup.ncr.correction,
                        root_cause=followup.ncr.root_cause,
                        systematic_corrective_action=followup.ncr.systematic_corrective_action,
                        corrective_action_details=followup.ncr.corrective_action_details,
                        expected_date_of_completion=followup.ncr.expected_date_of_completion,
                        actual_date_of_completion=followup.ncr.actual_date_of_completion,
                        edc_given_date=followup.ncr.edc_given_date,
                        remarks=followup.ncr.remarks,
                        followup_observations=followup.ncr.followup_observations,
                        followup_date=followup.ncr.followup_date,
                        rejected_reson=followup.ncr.rejected_reson,
                        rejected_count=followup.ncr.rejected_count,
                        closed_on=followup.ncr.closed_on,
                        files=[],
                        document_references=[],
                        team=[
                            NCRTeamResponse(
                                id=ncr_team.id,
                                user_id=ncr_team.user_id,
                                role=ncr_team.role,
                                ncr_id=ncr_team.ncr_id,
                                user=UserResponse(
                                    id=ncr_team.user.id,
                                    employee_id=ncr_team.user.employee_id,
                                    name=ncr_team.user.name,
                                ),
                            )
                            for ncr_team in followup.ncr.team
                        ],
                        audit_info=AuditInfoResponse(
                            id=followup.ncr.audit_info_id,
                            ref=followup.ncr.audit_info.ref,
                            department_id=followup.ncr.audit_info.department_id,
                            department=DepartmentResponse(
                                id=followup.ncr.audit_info.department.id,
                                name=followup.ncr.audit_info.department.name,
                                code=followup.ncr.audit_info.department.code,
                                created_at=followup.ncr.audit_info.department.created_at,
                                updated_at=followup.ncr.audit_info.department.updated_at,
                                slug=followup.ncr.audit_info.department.slug,
                            ),
                            from_date=followup.ncr.audit_info.from_date,
                            to_date=followup.ncr.audit_info.to_date,
                            closed_date=followup.ncr.audit_info.closed_date,
                            status=followup.ncr.audit_info.status,
                        ),
                    ),
                    created_at=followup.created_at,
                )
                for followup in followups
            ]
        

        return response

    async def get_followup_by_id(self, followup_id: UUID):
        followup = await self.session.execute(
            select(Followup)
            .where(Followup.id == followup_id)
            .options(
                selectinload(Followup.ncr).options(
                    selectinload(NCR.audit_info).options(
                        selectinload(AuditInfo.audit),
                        selectinload(AuditInfo.department),
                    ),
                ),
                selectinload(Followup.auditor),
                selectinload(Followup.requested_by),
            )
        )
        followup = followup.scalar_one_or_none()
        if not followup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Followup not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return FollowupResponse(
            id=followup.id,
            requested_date=followup.requested_date,
            status=followup.status,
            ncr_id=followup.ncr_id,
            auditor_id=followup.auditor_id,
            auditor=followup.auditor,
            requested_by_id=followup.requested_by_id,
            assgined_on=followup.assgined_on,
            completed_on=followup.completed_on,
            requested_by=followup.requested_by,
            ncr=NCRResponse(
                id=followup.ncr_id,
                status=followup.ncr.status,
                mode=followup.ncr.mode,
                shift=followup.ncr.shift,
                type=followup.ncr.type,
                audit_info_id=followup.ncr.audit_info_id,
                description=followup.ncr.description,
                objective_evidence=followup.ncr.objective_evidence,
                requirement=followup.ncr.requirement,
                main_clause=followup.ncr.main_clause,
                sub_clause=followup.ncr.sub_clause,
                ss_clause=followup.ncr.ss_clause,
                correction=followup.ncr.correction,
                root_cause=followup.ncr.root_cause,
                systematic_corrective_action=followup.ncr.systematic_corrective_action,
                corrective_action_details=followup.ncr.corrective_action_details,
                expected_date_of_completion=followup.ncr.expected_date_of_completion,
                actual_date_of_completion=followup.ncr.actual_date_of_completion,
                edc_given_date=followup.ncr.edc_given_date,
                remarks=followup.ncr.remarks,
                followup_observations=followup.ncr.followup_observations,
                followup_date=followup.ncr.followup_date,
                rejected_reson=followup.ncr.rejected_reson,
                rejected_count=followup.ncr.rejected_count,
                closed_on=followup.ncr.closed_on,
                files=[
                    NCRFiles(
                        id=ncr_file.id,
                        created_at=ncr_file.created_at,
                        updated_at=ncr_file.updated_at,
                        path=ncr_file.path,
                        file_type=ncr_file.file_type,
                    )
                    for ncr_file in followup.ncr.files
                ],
                document_references=[
                    DocumentReference(
                        id=document_reference.id,
                        created_at=document_reference.created_at,
                        updated_at=document_reference.updated_at,
                        ref=document_reference.ref,
                        page=document_reference.page,
                        paragraph=document_reference.paragraph,
                    )
                    for document_reference in followup.ncr.document_references
                ],
                team=[
                    NCRTeamResponse(
                        id=ncr_team.id,
                        user_id=ncr_team.user_id,
                        role=ncr_team.role,
                        user=ncr_team.user,
                    )
                    for ncr_team in followup.ncr.team
                ],
                audit_info=AuditInfoResponse(
                    id=followup.ncr.audit_info_id,
                    ref=followup.ncr.audit_info.ref,
                    department_id=followup.ncr.audit_info.department_id,
                    department=DepartmentResponse(
                        id=followup.ncr.audit_info.department.id,
                        name=followup.ncr.audit_info.department.name,
                        code=followup.ncr.audit_info.department.code,
                        created_at=followup.ncr.audit_info.department.created_at,
                        updated_at=followup.ncr.audit_info.department.updated_at,
                    ),
                    from_date=followup.ncr.audit_info.from_date,
                    to_date=followup.ncr.audit_info.to_date,
                    closed_date=followup.ncr.audit_info.closed_date,
                    status=followup.ncr.audit_info.status,
                    audit=AuditResponse(
                        id=followup.ncr.audit_info.audit.id,
                        ref=followup.ncr.audit_info.audit.ref,
                        type=followup.ncr.audit_info.audit.type,
                        schedule=followup.ncr.audit_info.audit.schedule,
                        plant=followup.ncr.audit_info.audit.plant,
                        created_at=followup.ncr.audit_info.audit.created_at,
                        updated_at=followup.ncr.audit_info.audit.updated_at,
                    ),
                ),
            ),
        )
