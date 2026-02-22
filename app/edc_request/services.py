from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func
from app.audit.models import Audit, AuditResponse
from app.audit_info.models import (
    AuditInfo,
    AuditInfoResponse,
    AuditTeam,
    AuditTeamResponse,
    AuditTeamRole,
)
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.mail import send_email
from app.edc_request.models import (
    CreateEdcRequestRequest,
    EDCStatus,
    EdcRequest,
    EdcRequestListResponse,
    EdcRequestResponse,
    UpdateEDCRequestRequest,
)
from app.ncr.models import (
    NCR,
    DocumentReference,
    NCRFiles,
    NCRResponse,
    NCRTeam,
    NCRTeamResponse,
    NCRTeamRole,
)
from app.core.config import settings
from app.settings.models import Department, DepartmentResponse, Plant
from sqlalchemy.orm import selectinload
from sqlmodel import select
from app.users.models import User, UserResponse
from app.utils.dsl_filter import apply_filters, apply_sort
from app.utils.model_graph import ModelGraph
from app.utils.serializer import to_naive


class EdcRequestService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build(
            [
                EdcRequest,
                NCR,
                AuditInfo,
                AuditTeam,
                NCRTeam,
                DocumentReference,
                NCRFiles,
                Department,
                Plant,
                Audit,
            ]
        )

    async def create_edc_request(
        self,
        data: CreateEdcRequestRequest,
        user_id: UUID,
        background_tasks: BackgroundTasks,
    ):
        ncr = await self.session.execute(
            select(NCR)
            .where(NCR.id == data.ncr_id)
            .options(
                selectinload(NCR.team).options(selectinload(NCRTeam.user)),
                selectinload(NCR.audit_info).options(
                    selectinload(AuditInfo.department),
                    selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
                ),
            )
        )
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

        if ncr.expected_date_of_completion > to_naive(data.new_edc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "New EDC cannot be earlier than current EDC",
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "data": None,
                },
            )

        is_edc_given = await self.session.execute(
            select(func.count())
            .select_from(EdcRequest)
            .where(EdcRequest.ncr_id == data.ncr_id)
        )

        if is_edc_given.scalar_one_or_none() > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "EDC Extension already requested for this NCR",
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "data": None,
                },
            )

        edc_request = EdcRequest(
            ncr_id=data.ncr_id,
            requested_by_id=user_id,
            old_edc=ncr.expected_date_of_completion,
            new_edc=to_naive(data.new_edc),
            comment=data.comment,
        )
        self.session.add(edc_request)
        await self.session.commit()

        hod = next(
            (
                member
                for member in ncr.audit_info.team
                if member.role == AuditTeamRole.HOD
            ),
            None,
        )

        auditor = next(
            (member for member in ncr.team if member.role == NCRTeamRole.CREATED_BY),
            None,
        )

        auditee = next(
            (member for member in ncr.team if member.role == NCRTeamRole.AUDITEE), None
        )

        background_tasks.add_task(
            send_email,
            [hod.user.email],
            f"ARe-Audit Management : EDC Extension Request ({ncr.ref})",
            {
                "user": hod.user.name,
                "message": (
                    f"<p>This is to inform you that an EDC extension request has been raised during the recent QMS Internal Audit. The details are as follows</p>"
                    f"<p><strong>Internal audit Ref. No:</strong> {ncr.audit_info.ref}</p>"
                    f"<p><strong>NCR Ref. No:</strong> {ncr.ref}</p>"
                    f"<p><strong>Audit Date:</strong> {ncr.created_at.strftime('%d %B %Y')}</p>"
                    f"<p><strong>Department:</strong> {ncr.audit_info.department.name}</p>"
                    f"<p><strong>Auditor:</strong> {auditor.user.name}</p>"
                    f"<p><strong>Auditee:</strong> {auditee.user.name}</p>"
                    f"<p><strong>Non-Conformity Description:</strong> {ncr.description}</p>"
                    f"<p><strong>Original EDC:</strong> {ncr.expected_date_of_completion}</p>"
                    f"<p><strong>New EDC:</strong> {data.new_edc}</p>"
                    f"<p><strong>Reason for Extension:</strong> {data.comment}</p>"
                    f"<p>Kindly review the above and provide your approval/confirmation for the revised EDC.</p>"
                ),
                "frontend_url": settings.FRONTEND_URL,
            },
        )
        return edc_request

    async def update_edc_request(
        self,
        edc_request_id: UUID,
        data: UpdateEDCRequestRequest,
        background_tasks: BackgroundTasks,
    ):
        edc_request = await self.session.execute(
            select(EdcRequest)
            .where(EdcRequest.id == edc_request_id)
            .options(selectinload(EdcRequest.requested_by))
        )
        edc_request = edc_request.scalar_one_or_none()

        if not edc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Edc request not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        if data.old_edc:
            edc_request.old_edc = to_naive(data.old_edc)
        if data.new_edc:
            edc_request.new_edc = to_naive(data.new_edc)
        if data.comment:
            edc_request.comment = data.comment
        if data.status:
            ncr = await self.session.execute(
                select(NCR).where(NCR.id == edc_request.ncr_id)
            )
            ncr = ncr.scalar_one_or_none()
            if data.status == EDCStatus.APPROVED:

                ncr.expected_date_of_completion = to_naive(data.new_edc)
                await self.session.commit()
                await self.session.refresh(ncr)

            background_tasks.add_task(
                send_email,
                [edc_request.requested_by.email],
                f"ARe-Audit Management : EDC Extension Request ({ncr.ref}) - {data.status}",
                {
                    "user": edc_request.requested_by.name,
                    "message": (
                        f"<p>Your EDC extension request for NCR Ref. No. {ncr.ref} has been {data.status.value.lower()}.</p>"
                        f"<p>Kindly update the EDC, correction, root cause, systemic corrective action, horizontal deployment, ADC, etc., in AReAMS within the specified timeline.</p>"
                    ),
                    "frontend_url": settings.FRONTEND_URL,
                },
            )
            edc_request.status = data.status
        await self.session.commit()
        return edc_request

    async def get_all_edc_requests(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(EdcRequest).options(
            selectinload(EdcRequest.ncr).options(
                selectinload(NCR.audit_info).options(
                    selectinload(AuditInfo.audit).options(
                        selectinload(Audit.plant).options(selectinload(Plant.company))
                    ),
                    selectinload(AuditInfo.department),
                    selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
                ),
            ),
            selectinload(EdcRequest.requested_by),
        )
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        if from_date:
            stmt = stmt.where(EdcRequest.created_at >= from_date)
        if to_date:
            stmt = stmt.where(EdcRequest.created_at <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, EdcRequest, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, EdcRequest, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        edc_requests = result.scalars().all()

        response = EdcRequestListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                EdcRequestResponse(
                    id=edc_request.id,
                    created_at=edc_request.created_at,
                    ncr_id=edc_request.ncr_id,
                    requested_by_id=edc_request.requested_by_id,
                    new_edc=edc_request.new_edc,
                    old_edc=edc_request.old_edc,
                    comment=edc_request.comment,
                    status=edc_request.status,
                    requested_by=UserResponse(
                        id=edc_request.requested_by_id,
                        employee_id=edc_request.requested_by.employee_id,
                        name=edc_request.requested_by.name,
                    ),
                    ncr=NCRResponse(
                        id=edc_request.ncr_id,
                        ref=edc_request.ncr.ref,
                        repeat=edc_request.ncr.repeat,
                        status=edc_request.ncr.status,
                        mode=edc_request.ncr.mode,
                        shift=edc_request.ncr.shift,
                        type=edc_request.ncr.type,
                        audit_info_id=edc_request.ncr.audit_info_id,
                        description=edc_request.ncr.description,
                        objective_evidence=edc_request.ncr.objective_evidence,
                        requirement=edc_request.ncr.requirement,
                        main_clause=edc_request.ncr.main_clause,
                        sub_clause=edc_request.ncr.sub_clause,
                        ss_clause=edc_request.ncr.ss_clause,
                        correction=edc_request.ncr.correction,
                        root_cause=edc_request.ncr.root_cause,
                        systematic_corrective_action=edc_request.ncr.systematic_corrective_action,
                        corrective_action_details=edc_request.ncr.corrective_action_details,
                        expected_date_of_completion=edc_request.ncr.expected_date_of_completion,
                        actual_date_of_completion=edc_request.ncr.actual_date_of_completion,
                        edc_given_date=edc_request.ncr.edc_given_date,
                        remarks=edc_request.ncr.remarks,
                        followup_observations=edc_request.ncr.followup_observations,
                        followup_date=edc_request.ncr.followup_date,
                        rejected_reson=edc_request.ncr.rejected_reson,
                        rejected_count=edc_request.ncr.rejected_count,
                        closed_on=edc_request.ncr.closed_on,
                        audit_info=AuditInfoResponse(
                            id=edc_request.ncr.audit_info_id,
                            ref=edc_request.ncr.audit_info.ref,
                            department_id=edc_request.ncr.audit_info.department_id,
                            department=DepartmentResponse(
                                id=edc_request.ncr.audit_info.department.id,
                                name=edc_request.ncr.audit_info.department.name,
                                code=edc_request.ncr.audit_info.department.code,
                                created_at=edc_request.ncr.audit_info.department.created_at,
                                updated_at=edc_request.ncr.audit_info.department.updated_at,
                                slug=edc_request.ncr.audit_info.department.slug,
                            ),
                            from_date=edc_request.ncr.audit_info.from_date,
                            to_date=edc_request.ncr.audit_info.to_date,
                            closed_date=edc_request.ncr.audit_info.closed_date,
                            status=edc_request.ncr.audit_info.status,
                        ),
                    ),
                )
                for edc_request in edc_requests
            ],
        )

        return response

    async def export_edc_requests(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = "created_at.desc",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ):
        stmt = select(EdcRequest).options(
            selectinload(EdcRequest.ncr).options(
                selectinload(NCR.audit_info).options(
                    selectinload(AuditInfo.audit).options(
                        selectinload(Audit.plant).options(selectinload(Plant.company))
                    ),
                    selectinload(AuditInfo.department),
                    selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
                ),
            ),
            selectinload(EdcRequest.requested_by),
        )
        from_date = to_naive(from_date)
        to_date = to_naive(to_date)
        if from_date:
            stmt = stmt.where(EdcRequest.created_at >= from_date)
        if to_date:
            stmt = stmt.where(EdcRequest.created_at <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, EdcRequest, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, EdcRequest, self.graph)

        result = await self.session.execute(stmt)
        edc_requests = result.scalars().all()

        response = [
            EdcRequestResponse(
                id=edc_request.id,
                created_at=edc_request.created_at,
                ncr_id=edc_request.ncr_id,
                requested_by_id=edc_request.requested_by_id,
                new_edc=edc_request.new_edc,
                old_edc=edc_request.old_edc,
                comment=edc_request.comment,
                status=edc_request.status,
                requested_by=UserResponse(
                    id=edc_request.requested_by_id,
                    employee_id=edc_request.requested_by.employee_id,
                    name=edc_request.requested_by.name,
                ),
                ncr=NCRResponse(
                    id=edc_request.ncr_id,
                    ref=edc_request.ncr.ref,
                    repeat=edc_request.ncr.repeat,
                    status=edc_request.ncr.status,
                    mode=edc_request.ncr.mode,
                    shift=edc_request.ncr.shift,
                    type=edc_request.ncr.type,
                    audit_info_id=edc_request.ncr.audit_info_id,
                    description=edc_request.ncr.description,
                    objective_evidence=edc_request.ncr.objective_evidence,
                    requirement=edc_request.ncr.requirement,
                    main_clause=edc_request.ncr.main_clause,
                    sub_clause=edc_request.ncr.sub_clause,
                    ss_clause=edc_request.ncr.ss_clause,
                    correction=edc_request.ncr.correction,
                    root_cause=edc_request.ncr.root_cause,
                    systematic_corrective_action=edc_request.ncr.systematic_corrective_action,
                    corrective_action_details=edc_request.ncr.corrective_action_details,
                    expected_date_of_completion=edc_request.ncr.expected_date_of_completion,
                    actual_date_of_completion=edc_request.ncr.actual_date_of_completion,
                    edc_given_date=edc_request.ncr.edc_given_date,
                    remarks=edc_request.ncr.remarks,
                    followup_observations=edc_request.ncr.followup_observations,
                    followup_date=edc_request.ncr.followup_date,
                    rejected_reson=edc_request.ncr.rejected_reson,
                    rejected_count=edc_request.ncr.rejected_count,
                    closed_on=edc_request.ncr.closed_on,
                    audit_info=AuditInfoResponse(
                        id=edc_request.ncr.audit_info_id,
                        ref=edc_request.ncr.audit_info.ref,
                        department_id=edc_request.ncr.audit_info.department_id,
                        department=DepartmentResponse(
                            id=edc_request.ncr.audit_info.department.id,
                            name=edc_request.ncr.audit_info.department.name,
                            code=edc_request.ncr.audit_info.department.code,
                            created_at=edc_request.ncr.audit_info.department.created_at,
                            updated_at=edc_request.ncr.audit_info.department.updated_at,
                            slug=edc_request.ncr.audit_info.department.slug,
                        ),
                        from_date=edc_request.ncr.audit_info.from_date,
                        to_date=edc_request.ncr.audit_info.to_date,
                        closed_date=edc_request.ncr.audit_info.closed_date,
                        status=edc_request.ncr.audit_info.status,
                    ),
                ),
            )
            for edc_request in edc_requests
        ]

        return response

    async def get_edc_request_by_id(self, edc_request_id: UUID):
        edc_request = await self.session.execute(
            select(EdcRequest)
            .where(EdcRequest.id == edc_request_id)
            .options(
                selectinload(EdcRequest.ncr).options(
                    selectinload(NCR.audit_info).options(
                        selectinload(AuditInfo.audit),
                        selectinload(AuditInfo.department),
                    ),
                ),
                selectinload(EdcRequest.requested_by),
            )
        )
        edc_request = edc_request.scalar_one_or_none()
        if not edc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Edc request not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        return EdcRequestResponse(
            id=edc_request.id,
            ncr_id=edc_request.ncr_id,
            requested_by_id=edc_request.requested_by_id,
            new_edc=edc_request.new_edc,
            old_edc=edc_request.old_edc,
            comment=edc_request.comment,
            status=edc_request.status,
            ncr=NCRResponse(
                id=edc_request.ncr_id,
                status=edc_request.ncr.status,
                mode=edc_request.ncr.mode,
                shift=edc_request.ncr.shift,
                type=edc_request.ncr.type,
                audit_info_id=edc_request.ncr.audit_info_id,
                description=edc_request.ncr.description,
                objective_evidence=edc_request.ncr.objective_evidence,
                requirement=edc_request.ncr.requirement,
                main_clause=edc_request.ncr.main_clause,
                sub_clause=edc_request.ncr.sub_clause,
                ss_clause=edc_request.ncr.ss_clause,
                correction=edc_request.ncr.correction,
                root_cause=edc_request.ncr.root_cause,
                systematic_corrective_action=edc_request.ncr.systematic_corrective_action,
                corrective_action_details=edc_request.ncr.corrective_action_details,
                expected_date_of_completion=edc_request.ncr.expected_date_of_completion,
                actual_date_of_completion=edc_request.ncr.actual_date_of_completion,
                edc_given_date=edc_request.ncr.edc_given_date,
                remarks=edc_request.ncr.remarks,
                followup_observations=edc_request.ncr.followup_observations,
                followup_date=edc_request.ncr.followup_date,
                rejected_reson=edc_request.ncr.rejected_reson,
                rejected_count=edc_request.ncr.rejected_count,
                closed_on=edc_request.ncr.closed_on,
                audit_info=AuditInfoResponse(
                    id=edc_request.ncr.audit_info_id,
                    ref=edc_request.ncr.audit_info.ref,
                    department_id=edc_request.ncr.audit_info.department_id,
                    department=DepartmentResponse(
                        id=edc_request.ncr.audit_info.department.id,
                        name=edc_request.ncr.audit_info.department.name,
                        code=edc_request.ncr.audit_info.department.code,
                        created_at=edc_request.ncr.audit_info.department.created_at,
                        updated_at=edc_request.ncr.audit_info.department.updated_at,
                    ),
                    from_date=edc_request.ncr.audit_info.from_date,
                    to_date=edc_request.ncr.audit_info.to_date,
                    closed_date=edc_request.ncr.audit_info.closed_date,
                    status=edc_request.ncr.audit_info.status,
                    audit=AuditResponse(
                        id=edc_request.ncr.audit_info.audit.id,
                        ref=edc_request.ncr.audit_info.audit.ref,
                        type=edc_request.ncr.audit_info.audit.type,
                        schedule=edc_request.ncr.audit_info.audit.schedule,
                        plant=edc_request.ncr.audit_info.audit.plant,
                        created_at=edc_request.ncr.audit_info.audit.created_at,
                        updated_at=edc_request.ncr.audit_info.audit.updated_at,
                    ),
                ),
            ),
        )
