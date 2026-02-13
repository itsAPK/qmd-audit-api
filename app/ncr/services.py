from datetime import datetime
from typing import Optional

from sqlalchemy import and_, case, func, literal, or_, union_all
from app.audit.models import Audit, AuditResponse
from app.audit_info.models import (
    AuditInfo,
    AuditInfoResponse,
    AuditTeam,
    AuditTeamResponse,
)
from app.core.config import settings
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.mail import send_email
from app.ncr.models import (
    NCR,
    CreateDocumentReferenceRequest,
    DocumentReference,
    NCRClauses,
    NCRClausesRequest,
    NCRCreateRequest,
    NCRFileType,
    NCRFiles,
    NCRShiftCreateRequest,
    NCRShift,
    NCRStatus,
    NCRTeam,
    NCRTeamCreateRequest,
    NCRTeamResponse,
    NCRTeamRole,
    NCRUpdateRequest,
    NCRResponse,
    NCRListResponse,
)
from sqlalchemy.orm import selectinload
from sqlmodel import select
from uuid import UUID
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import aliased
from app.settings.models import (
    Company,
    CompanyResponse,
    DepartmentResponse,
    Plant,
    PlantResponse,
    Department,
)
from app.users.models import User, UserResponse
from app.utils.dsl_filter import apply_filters, apply_sort
from app.utils.model_graph import ModelGraph
from app.utils.serializer import to_naive
from app.audit.models import Audit


class NCRService:
    def __init__(self, session):
        self.session = session
        self.graph = ModelGraph()
        self.graph.build(
            [
                NCR,
                AuditInfo,
                AuditTeam,
                NCRTeam,
                DocumentReference,
                NCRFiles,
                Audit,
                Plant,
                Department,
            ]
        )
        self.CLAUSE_TYPE_MAP = {
            "MAIN": "MAIN CLAUSE",
            "MAIN CLAUSE": "MAIN CLAUSE",
            "SUB": "SUB CLAUSE",
            "SUB CLAUSE": "SUB CLAUSE",
            "SS": "SUB-SUB CLAUSE",
            "SUB-SUB CLAUSE": "SUB-SUB CLAUSE",
        }
        self.ALL_NCR_STATUSES = [s.value for s in NCRStatus]

    async def create_ncr(
        self, data: NCRCreateRequest, user_id: UUID, background_tasks: BackgroundTasks
    ):

        result = await self.session.execute(
            select(AuditInfo)
            .where(AuditInfo.id == data.audit_info_id)
            .options(
                selectinload(AuditInfo.ncrs),
                selectinload(AuditInfo.department),
                selectinload(AuditInfo.team),
                selectinload(AuditInfo.audit).options(
                    selectinload(Audit.plant).options(selectinload(Plant.company))
                ),
            )
        )
        audit_info = result.scalar_one_or_none()

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

        audit = audit_info.audit
        plant = audit.plant
        company = plant.company
        department = audit_info.department

        year = datetime.now().year
        ref = (
            f"{year}-{year + 1}/"
            f"{audit.type}{audit.schedule}/"
            f"{len(audit_info.ncrs) + 1}/"
            f"{department.code}/"
            f"{company.code}-{plant.code}"
        )

        auditee = await self.session.execute(
            select(User).where(User.id == data.auditee_id)
        )
        auditee = auditee.scalar_one_or_none()
        if not auditee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        created_by = await self.session.execute(select(User).where(User.id == user_id))
        created_by = created_by.scalar_one_or_none()
        if not created_by:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "User not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )

        ncr_new = NCR(
            ref=ref,
            status="CREATED",
            mode=data.mode,
            shift=data.shift,
            type=data.type,
            repeat=data.repeat,
            audit_info_id=data.audit_info_id,
            description=data.description,
            objective_evidence=data.objective_evidence,
            requirement=data.requirement,
            main_clause=data.main_clause,
            sub_clause=data.sub_clause,
            ss_clause=data.ss_clause,
        )
        self.session.add(ncr_new)

        for document_reference in data.document_references:
            document_reference = DocumentReference(
                ref=document_reference.ref,
                page=document_reference.page,
                paragraph=document_reference.paragraph,
                ncr_id=ncr_new.id,
            )
            self.session.add(document_reference)

        created_team = NCRTeam(
            user_id=user_id,
            role_id=NCRTeamRole.CREATED_BY,
            ncr_id=ncr_new.id,
        )
        self.session.add(created_team)

        auditee_team = NCRTeam(
            user_id=data.auditee_id,
            role_id=NCRTeamRole.AUDITEE,
            ncr_id=ncr_new.id,
        )
        self.session.add(auditee_team)
        await self.session.commit()
        await self.session.refresh(ncr_new)

        background_tasks.add_task(
            send_email,
            [auditee.email],
            f"Non-Conformity Raised {ncr_new.ref} by {created_by.name}",
            {
                "user": auditee.name,
                "message": (
                    f"<p>This is to inform you that a <strong>Non-Conformity (NCR)</strong> has been raised for your department during the recent QMS Internal Audit.</p>"
                    f"<p><strong>Internal Audit Reference No.:</strong> {audit_info.ref}</p>"
                    f"<p><strong>Audit Date:</strong> {datetime.now().strftime('%d %B %Y')}</p>"
                    f"<p><strong>Non-Conformity Description:</strong> {data.description}</p>"
                    f"<p><strong>Auditor:</strong> {created_by.name}</p>"
                    f"<p><strong>Note:</strong></p>"
                    f"<ul>"
                    f"<li>Kindly update the EDC, correction, root cause, systemic corrective action, horizontal deployment, ADC, etc., in AReAMS within the specified timeline.</li>"
                    f"</ul>"
                    f"<p>For any clarification or support, please feel free to contact the QMS Department.</p>"
                ),
                "frontend_url": settings.FRONTEND_URL,
            },
        )

        return ncr_new

    async def update_ncr(self, ncr_id: UUID, data: NCRUpdateRequest):
        ncr = await self.session.execute(
            select(NCR).where(NCR.id == ncr_id).options(selectinload(NCR.audit_info))
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
        if data.auditee_id:
            auditee = await self.session.execute(
                select(NCRTeam).where(
                    NCRTeam.ncr_id == ncr_id, role=NCRTeamRole.AUDITEE
                )
            )
            auditee = auditee.scalar_one_or_none()
            if auditee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Auditee already exists",
                        "success": False,
                        "status": status.HTTP_400_BAD_REQUEST,
                        "data": None,
                    },
                )
            auditee.user_id = data.auditee_id
            auditee.role_id = NCRTeamRole.AUDITEE

            await self.session.commit()
            await self.session.refresh(ncr)
        if data.shift:
            ncr.shift = data.shift

        if data.status:
            if data.status == NCRStatus.REJECTED:
                ncr.rejected_count = ncr.rejected_count + 1

            if data.status == NCRStatus.CLOSED:
                ncr.closed_on = datetime.now()
            
            if data.status == NCRStatus.FOLLOW_COMPLETED:
                ncr.actual_date_of_completion = datetime.now()

            ncr.status = data.status

        if data.type:
            ncr.type = data.type

        if data.repeat:
            ncr.repeat = data.repeat

        if data.audit_info_id:

            ncr.audit_info_id = data.audit_info_id

        if data.description:
            ncr.description = data.description

        if data.objective_evidence:
            ncr.objective_evidence = data.objective_evidence

        if data.requirement:
            ncr.requirement = data.requirement

        if data.main_clause:
            ncr.main_clause = data.main_clause

        if data.sub_clause:
            ncr.sub_clause = data.sub_clause

        if data.ss_clause:
            ncr.ss_clause = data.ss_clause

        if data.correction:
            ncr.correction = data.correction

        if data.root_cause:
            ncr.root_cause = data.root_cause

        if data.systematic_corrective_action:
            ncr.systematic_corrective_action = data.systematic_corrective_action

        if data.corrective_action_details:
            ncr.corrective_action_details = data.corrective_action_details

        if data.expected_date_of_completion:

            ncr.expected_date_of_completion = to_naive(data.expected_date_of_completion)
            ncr.edc_given_date = to_naive(data.expected_date_of_completion)

        if data.actual_date_of_completion:
            ncr.actual_date_of_completion = to_naive(data.actual_date_of_completion)

        if data.edc_given_date:
            ncr.edc_given_date = to_naive(data.edc_given_date)

        if data.remarks:
            ncr.remarks = data.remarks

        if data.followup_observations:
            ncr.followup_observations = data.followup_observations

        if data.followup_date:
            ncr.followup_date = data.followup_date

        if data.rejected_reson:
            ncr.rejected_reson = data.rejected_reson

        if data.rejected_count:
            ncr.rejected_count = data.rejected_count

        if data.closed_on:
            ncr.closed_on = data.closed_on

        if data.document_references:
            for document_reference in data.document_references:
                document_reference = DocumentReference(
                    ref=document_reference.ref,
                    page=document_reference.page,
                    paragraph=document_reference.paragraph,
                    ncr_id=ncr_id,
                )
                self.session.add(document_reference)
            await self.session.commit()

        await self.session.commit()
        await self.session.refresh(ncr)

        return ncr

    async def get_ncr(self, ncr_id: UUID):
        ncr = await self.session.execute(
            select(NCR)
            .where(NCR.id == ncr_id)
            .options(
                selectinload(NCR.team).options(selectinload(NCRTeam.user)),
                selectinload(NCR.document_references),
                selectinload(NCR.files),
                selectinload(NCR.audit_info).options(
                    selectinload(AuditInfo.audit).options(
                        selectinload(Audit.plant).options(selectinload(Plant.company))
                    ),
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
        return NCRResponse(
            id=ncr.id,
            created_at=ncr.created_at,
            ref=ncr.ref,
            mode=ncr.mode,
            shift=ncr.shift,
            type=ncr.type,
            status=ncr.status,
            repeat=ncr.repeat,
            audit_info_id=ncr.audit_info_id,
            description=ncr.description,
            objective_evidence=ncr.objective_evidence,
            requirement=ncr.requirement,
            main_clause=ncr.main_clause,
            sub_clause=ncr.sub_clause,
            ss_clause=ncr.ss_clause,
            correction=ncr.correction,
            root_cause=ncr.root_cause,
            systematic_corrective_action=ncr.systematic_corrective_action,
            corrective_action_details=ncr.corrective_action_details,
            expected_date_of_completion=ncr.expected_date_of_completion,
            actual_date_of_completion=ncr.actual_date_of_completion,
            edc_given_date=ncr.edc_given_date,
            remarks=ncr.remarks,
            followup_observations=ncr.followup_observations,
            followup_date=ncr.followup_date,
            rejected_reson=ncr.rejected_reson,
            rejected_count=ncr.rejected_count,
            closed_on=ncr.closed_on,
            files=[
                NCRFiles(
                    id=ncr_file.id,
                    created_at=ncr_file.created_at,
                    updated_at=ncr_file.updated_at,
                    path=ncr_file.path,
                    file_type=ncr_file.file_type,
                )
                for ncr_file in ncr.files
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
                for document_reference in ncr.document_references
            ],
            team=[
                NCRTeamResponse(
                    id=ncr_team.id,
                    user_id=ncr_team.user_id,
                    ncr_id=ncr.id,
                    role=ncr_team.role,
                    user=UserResponse(
                        id=ncr_team.user_id,
                        employee_id=ncr_team.user.employee_id,
                        password=ncr_team.user.password,
                        email=ncr_team.user.email,
                        qualification=ncr_team.user.qualification,
                        designation=ncr_team.user.designation,
                        is_active=ncr_team.user.is_active,
                        role=ncr_team.user.role,
                        departments=[],
                        name=ncr_team.user.name,
                    ),
                )
                for ncr_team in ncr.team
            ],
            audit_info=AuditInfoResponse(
                id=ncr.audit_info_id,
                ref=ncr.audit_info.ref,
                department_id=ncr.audit_info.department_id,
                department=DepartmentResponse(
                    id=ncr.audit_info.department.id,
                    name=ncr.audit_info.department.name,
                    code=ncr.audit_info.department.code,
                    created_at=ncr.audit_info.department.created_at,
                    updated_at=ncr.audit_info.department.updated_at,
                    slug=ncr.audit_info.department.slug,
                ),
                from_date=ncr.audit_info.from_date,
                to_date=ncr.audit_info.to_date,
                closed_date=ncr.audit_info.closed_date,
                status=ncr.audit_info.status,
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
                    for audit_team in ncr.audit_info.team
                ],
                audit=AuditResponse(
                    id=ncr.audit_info.audit.id,
                    ref=ncr.audit_info.audit.ref,
                    type=ncr.audit_info.audit.type,
                    schedule=ncr.audit_info.audit.schedule,
                    created_at=ncr.audit_info.audit.created_at,
                    updated_at=ncr.audit_info.audit.updated_at,
                    standard=ncr.audit_info.audit.standard,
                    start_date=ncr.audit_info.audit.start_date,
                    end_date=ncr.audit_info.audit.end_date,
                    plant=PlantResponse(
                        id=ncr.audit_info.audit.plant.id,
                        name=ncr.audit_info.audit.plant.name,
                        code=ncr.audit_info.audit.plant.code,
                        created_at=ncr.audit_info.audit.plant.created_at,
                        updated_at=ncr.audit_info.audit.plant.updated_at,
                        company_id=ncr.audit_info.audit.plant.company.id,
                        company=CompanyResponse(
                            id=ncr.audit_info.audit.plant.company.id,
                            name=ncr.audit_info.audit.plant.company.name,
                            code=ncr.audit_info.audit.plant.company.code,
                            created_at=ncr.audit_info.audit.plant.company.created_at,
                            updated_at=ncr.audit_info.audit.plant.company.updated_at,
                        ),
                    ),
                    plant_id=ncr.audit_info.audit.plant.id,
                ),
            ),
        )

    async def get_all_ncrs(
        self,
        filters: Optional[str] = None,
        sort: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        stmt = select(NCR).options(
            selectinload(NCR.team).options(selectinload(NCRTeam.user)),
            selectinload(NCR.document_references),
            selectinload(NCR.files),
            selectinload(NCR.audit_info).options(
                selectinload(AuditInfo.audit).options(
                    selectinload(Audit.plant).options(selectinload(Plant.company))
                ),
                selectinload(AuditInfo.department),
                selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
            ),
        )
        if from_date:
            form_date = to_naive(from_date)
            stmt = stmt.where(NCR.created_at >= form_date)

        if to_date:
            to_date = to_naive(to_date)
            stmt = stmt.where(NCR.created_at <= to_date)

        if filters:
            stmt = apply_filters(stmt, filters, NCR, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, NCR, self.graph)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size).distinct()

        result = await self.session.execute(stmt)
        ncrs = result.scalars().all()

        response = NCRListResponse(
            total=total,
            current_page=page,
            page_size=page_size,
            total_pages=total // page_size + 1,
            data=[
                NCRResponse(
                    id=ncr.id,
                    created_at=ncr.created_at,
                    ref=ncr.ref,
                    mode=ncr.mode,
                    shift=ncr.shift,
                    type=ncr.type,
                    status=ncr.status,
                    repeat=ncr.repeat,
                    audit_info_id=ncr.audit_info_id,
                    description=ncr.description,
                    objective_evidence=ncr.objective_evidence,
                    requirement=ncr.requirement,
                    main_clause=ncr.main_clause,
                    sub_clause=ncr.sub_clause,
                    ss_clause=ncr.ss_clause,
                    correction=ncr.correction,
                    root_cause=ncr.root_cause,
                    systematic_corrective_action=ncr.systematic_corrective_action,
                    corrective_action_details=ncr.corrective_action_details,
                    expected_date_of_completion=ncr.expected_date_of_completion,
                    actual_date_of_completion=ncr.actual_date_of_completion,
                    edc_given_date=ncr.edc_given_date,
                    remarks=ncr.remarks,
                    followup_observations=ncr.followup_observations,
                    followup_date=ncr.followup_date,
                    rejected_reson=ncr.rejected_reson,
                    rejected_count=ncr.rejected_count,
                    closed_on=ncr.closed_on,
                    files=[
                        NCRFiles(
                            id=ncr_file.id,
                            created_at=ncr_file.created_at,
                            updated_at=ncr_file.updated_at,
                            path=ncr_file.path,
                            file_type=ncr_file.file_type,
                        )
                        for ncr_file in ncr.files
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
                        for document_reference in ncr.document_references
                    ],
                    team=[
                        NCRTeamResponse(
                            id=ncr_team.id,
                            user_id=ncr_team.user_id,
                            ncr_id=ncr.id,
                            role=ncr_team.role,
                            user=UserResponse(
                                id=ncr_team.user_id,
                                employee_id=ncr_team.user.employee_id,
                                password=ncr_team.user.password,
                                email=ncr_team.user.email,
                                qualification=ncr_team.user.qualification,
                                designation=ncr_team.user.designation,
                                is_active=ncr_team.user.is_active,
                                role=ncr_team.user.role,
                                departments=[],
                                name=ncr_team.user.name,
                            ),
                        )
                        for ncr_team in ncr.team
                    ],
                    audit_info=AuditInfoResponse(
                        id=ncr.audit_info_id,
                        ref=ncr.audit_info.ref,
                        department_id=ncr.audit_info.department_id,
                        department=DepartmentResponse(
                            id=ncr.audit_info.department.id,
                            name=ncr.audit_info.department.name,
                            code=ncr.audit_info.department.code,
                            created_at=ncr.audit_info.department.created_at,
                            updated_at=ncr.audit_info.department.updated_at,
                            slug=ncr.audit_info.department.slug,
                        ),
                        from_date=ncr.audit_info.from_date,
                        to_date=ncr.audit_info.to_date,
                        closed_date=ncr.audit_info.closed_date,
                        status=ncr.audit_info.status,
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
                            for audit_team in ncr.audit_info.team
                        ],
                        audit=AuditResponse(
                            id=ncr.audit_info.audit.id,
                            ref=ncr.audit_info.audit.ref,
                            type=ncr.audit_info.audit.type,
                            schedule=ncr.audit_info.audit.schedule,
                            created_at=ncr.audit_info.audit.created_at,
                            updated_at=ncr.audit_info.audit.updated_at,
                            standard=ncr.audit_info.audit.standard,
                            start_date=ncr.audit_info.audit.start_date,
                            end_date=ncr.audit_info.audit.end_date,
                            plant=PlantResponse(
                                id=ncr.audit_info.audit.plant.id,
                                name=ncr.audit_info.audit.plant.name,
                                code=ncr.audit_info.audit.plant.code,
                                created_at=ncr.audit_info.audit.plant.created_at,
                                updated_at=ncr.audit_info.audit.plant.updated_at,
                                company_id=ncr.audit_info.audit.plant.company.id,
                                company=CompanyResponse(
                                    id=ncr.audit_info.audit.plant.company.id,
                                    name=ncr.audit_info.audit.plant.company.name,
                                    code=ncr.audit_info.audit.plant.company.code,
                                    created_at=ncr.audit_info.audit.plant.company.created_at,
                                    updated_at=ncr.audit_info.audit.plant.company.updated_at,
                                ),
                            ),
                            plant_id=ncr.audit_info.audit.plant.id,
                        ),
                    ),
                )
                for ncr in ncrs
            ],
        )

        return response

    async def export_all_ncrs(
        self, filters: Optional[str] = None, sort: Optional[str] = None
    ):
        stmt = select(NCR).options(
            selectinload(NCR.team).options(selectinload(NCRTeam.user)),
            selectinload(NCR.document_references),
            selectinload(NCR.files),
            selectinload(NCR.audit_info).options(
                selectinload(AuditInfo.audit).options(
                    selectinload(Audit.plant).options(selectinload(Plant.company))
                ),
                selectinload(AuditInfo.department),
                selectinload(AuditInfo.team).options(selectinload(AuditTeam.user)),
            ),
        )

        if filters:
            stmt = apply_filters(stmt, filters, NCR, self.graph)

        if sort:
            stmt = apply_sort(stmt, sort, NCR, self.graph)

        result = await self.session.execute(stmt)
        ncrs = result.scalars().all()
        response = [
            NCRResponse(
                id=ncr.id,
                ref=ncr.ref,
                created_at=ncr.created_at,
                mode=ncr.mode,
                shift=ncr.shift,
                type=ncr.type,
                status=ncr.status,
                repeat=ncr.repeat,
                audit_info_id=ncr.audit_info_id,
                description=ncr.description,
                objective_evidence=ncr.objective_evidence,
                requirement=ncr.requirement,
                main_clause=ncr.main_clause,
                sub_clause=ncr.sub_clause,
                ss_clause=ncr.ss_clause,
                correction=ncr.correction,
                root_cause=ncr.root_cause,
                systematic_corrective_action=ncr.systematic_corrective_action,
                corrective_action_details=ncr.corrective_action_details,
                expected_date_of_completion=ncr.expected_date_of_completion,
                actual_date_of_completion=ncr.actual_date_of_completion,
                edc_given_date=ncr.edc_given_date,
                remarks=ncr.remarks,
                followup_observations=ncr.followup_observations,
                followup_date=ncr.followup_date,
                rejected_reson=ncr.rejected_reson,
                rejected_count=ncr.rejected_count,
                closed_on=ncr.closed_on,
                files=[
                    NCRFiles(
                        id=ncr_file.id,
                        created_at=ncr_file.created_at,
                        updated_at=ncr_file.updated_at,
                        path=ncr_file.path,
                        file_type=ncr_file.file_type,
                    )
                    for ncr_file in ncr.files
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
                    for document_reference in ncr.document_references
                ],
                team=[
                    NCRTeamResponse(
                        id=ncr_team.id,
                        user_id=ncr_team.user_id,
                        ncr_id=ncr.id,
                        role=ncr_team.role,
                        user=UserResponse(
                            id=ncr_team.user_id,
                            employee_id=ncr_team.user.employee_id,
                            password=ncr_team.user.password,
                            email=ncr_team.user.email,
                            qualification=ncr_team.user.qualification,
                            designation=ncr_team.user.designation,
                            is_active=ncr_team.user.is_active,
                            role=ncr_team.user.role,
                            departments=[],
                            name=ncr_team.user.name,
                        ),
                    )
                    for ncr_team in ncr.team
                ],
                audit_info=AuditInfoResponse(
                    id=ncr.audit_info_id,
                    ref=ncr.audit_info.ref,
                    department_id=ncr.audit_info.department_id,
                    department=DepartmentResponse(
                        id=ncr.audit_info.department.id,
                        name=ncr.audit_info.department.name,
                        code=ncr.audit_info.department.code,
                        created_at=ncr.audit_info.department.created_at,
                        updated_at=ncr.audit_info.department.updated_at,
                        slug=ncr.audit_info.department.slug,
                    ),
                    from_date=ncr.audit_info.from_date,
                    to_date=ncr.audit_info.to_date,
                    closed_date=ncr.audit_info.closed_date,
                    status=ncr.audit_info.status,
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
                        for audit_team in ncr.audit_info.team
                    ],
                    audit=AuditResponse(
                        id=ncr.audit_info.audit.id,
                        ref=ncr.audit_info.audit.ref,
                        type=ncr.audit_info.audit.type,
                        schedule=ncr.audit_info.audit.schedule,
                        created_at=ncr.audit_info.audit.created_at,
                        updated_at=ncr.audit_info.audit.updated_at,
                        standard=ncr.audit_info.audit.standard,
                        start_date=ncr.audit_info.audit.start_date,
                        end_date=ncr.audit_info.audit.end_date,
                        plant=PlantResponse(
                            id=ncr.audit_info.audit.plant.id,
                            name=ncr.audit_info.audit.plant.name,
                            code=ncr.audit_info.audit.plant.code,
                            created_at=ncr.audit_info.audit.plant.created_at,
                            updated_at=ncr.audit_info.audit.plant.updated_at,
                            company_id=ncr.audit_info.audit.plant.company.id,
                            company=CompanyResponse(
                                id=ncr.audit_info.audit.plant.company.id,
                                name=ncr.audit_info.audit.plant.company.name,
                                code=ncr.audit_info.audit.plant.company.code,
                                created_at=ncr.audit_info.audit.plant.company.created_at,
                                updated_at=ncr.audit_info.audit.plant.company.updated_at,
                            ),
                        ),
                        plant_id=ncr.audit_info.audit.plant.id,
                    ),
                ),
            )
            for ncr in ncrs
        ]

        return response

    async def delete_ncr(self, ncr_id: UUID):
        ncr = await self.session.execute(select(NCR).where(NCR.id == ncr_id))
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
        await self.session.delete(ncr)
        await self.session.commit()
        return ncr

    async def create_shift(self, data: NCRShiftCreateRequest):
        ncr_shift = NCRShift(
            name=data.name,
        )
        self.session.add(ncr_shift)
        await self.session.commit()
        return ncr_shift

    async def get_all_shifts(self):
        ncr_shifts = await self.session.execute(select(NCRShift))
        ncr_shifts = ncr_shifts.scalars().all()
        return ncr_shifts

    async def update_shift(self, shift_id: UUID, request: NCRShiftCreateRequest):
        ncr_shift = await self.session.execute(
            select(NCRShift).where(NCRShift.id == shift_id)
        )
        ncr_shift = ncr_shift.scalar_one_or_none()

        if not ncr_shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Shift not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        ncr_shift.name = request.name
        await self.session.commit()
        return ncr_shift

    async def delete_shift(self, shift_id: UUID):
        ncr_shift = await self.session.execute(
            select(NCRShift).where(NCRShift.id == shift_id)
        )
        ncr_shift = ncr_shift.scalar_one_or_none()

        if not ncr_shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Shift not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(ncr_shift)
        await self.session.commit()
        return ncr_shift

    async def upload_files(self, ncr_id: UUID, file: str, file_type: NCRFileType):
        ncr = await self.session.execute(select(NCR).where(NCR.id == ncr_id))
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

        ncr_file = NCRFiles(
            ncr_id=ncr_id,
            path=file,
            file_type=file_type,
        )
        self.session.add(ncr_file)
        await self.session.commit()
        return ncr

    async def add_document_reference(
        self, ncr_id: UUID, document_reference: CreateDocumentReferenceRequest
    ):
        ncr = await self.session.execute(select(NCR).where(NCR.id == ncr_id))
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

        document = DocumentReference(
            ref=document_reference.ref,
            page=document_reference.page,
            paragraph=document_reference.paragraph,
            ncr_id=ncr_id,
        )
        self.session.add(document)
        await self.session.commit()
        return ncr

    async def delete_document_reference(
        self, ncr_id: UUID, document_reference_id: UUID
    ):
        ncr = await self.session.execute(select(NCR).where(NCR.id == ncr_id))
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

        document = await self.session.execute(
            select(DocumentReference).where(
                DocumentReference.id == document_reference_id
            )
        )
        document = document.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Document reference not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(document)
        await self.session.commit()
        return ncr

    async def add_ncr_team(self, team: NCRTeamCreateRequest):
        ncr = await self.session.execute(select(NCR).where(NCR.id == team.ncr_id))
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

        ncr_team = NCRTeam(
            user_id=team.user_id,
            role=team.role,
            ncr_id=team.ncr_id,
        )
        self.session.add(ncr_team)
        await self.session.commit()

    async def delete_ncr_team(self, ncr_id: UUID, team_id: UUID):
        ncr = await self.session.execute(select(NCR).where(NCR.id == ncr_id))
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

        ncr_team = await self.session.execute(
            select(NCRTeam).where(NCRTeam.id == team_id)
        )
        ncr_team = ncr_team.scalar_one_or_none()

        if not ncr_team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "NCR team not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(ncr_team)
        await self.session.commit()
        check = await self.session.execute(select(NCRTeam).where(NCRTeam.id == team_id))
        print("TEAM AFTER DELETE:", check.scalar_one_or_none())
        return ncr

    async def add_clause(self, data: NCRClausesRequest):

        ncr_clause = NCRClauses(
            clause=data.clause,
            type=data.type,
        )
        self.session.add(ncr_clause)
        await self.session.commit()
        return ncr_clause

    async def get_clauses(self):
        ncr_clauses = await self.session.execute(select(NCRClauses))
        ncr_clauses = ncr_clauses.scalars().all()
        return ncr_clauses

    async def update_clause(self, clause_id: UUID, data: NCRClausesRequest):
        ncr_clause = await self.session.execute(
            select(NCRClauses).where(NCRClauses.id == clause_id)
        )
        ncr_clause = ncr_clause.scalar_one_or_none()

        if not ncr_clause:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "NCR clause not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        ncr_clause.clause = data.clause
        ncr_clause.type = data.type
        await self.session.commit()
        return ncr_clause

    async def delete_clause(self, clause_id: UUID):
        ncr_clause = await self.session.execute(
            select(NCRClauses).where(NCRClauses.id == clause_id)
        )
        ncr_clause = ncr_clause.scalar_one_or_none()

        if not ncr_clause:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "NCR clause not found",
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "data": None,
                },
            )
        await self.session.delete(ncr_clause)
        await self.session.commit()

    async def get_clause_ncr_stats(
        self,
        plant_id: Optional[UUID] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ):
        CLAUSE_TYPES = ["MAIN CLAUSE", "SUB CLAUSE", "SUB-SUB CLAUSE"]

        filters = []

        if created_from:
            filters.append(NCR.created_at >= to_naive(created_from))

        if created_to:
            filters.append(NCR.created_at <= to_naive(created_to))

        if plant_id:
            filters.append(Plant.id == plant_id)

        audit_refs = (
            (
                await self.session.execute(
                    select(Audit.ref)
                    .join(AuditInfo, Audit.id == AuditInfo.audit_id)
                    .join(NCR, NCR.audit_info_id == AuditInfo.id)
                    .join(Plant, Audit.plant_id == Plant.id)
                    .where(*filters)
                    .distinct()
                )
            )
            .scalars()
            .all()
        )

        clause_rows = (
            await self.session.execute(select(NCRClauses.clause, NCRClauses.type))
        ).all()

        master: dict = {}

        for clause, ctype in clause_rows:
            if clause and ctype:
                master[(ctype, clause)] = [
                    {"audit_ref": ar, "count": 0, "ncr": []} for ar in audit_refs
                ]

        def agg_query(label, column):
            return (
                select(
                    literal(label).label("ctype"),
                    column.label("cvalue"),
                    Audit.ref.label("audit_ref"),
                    func.count(NCR.id).label("cnt"),
                )
                .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
                .join(Audit, AuditInfo.audit_id == Audit.id)
                .join(Plant, Audit.plant_id == Plant.id)
                .where(column.isnot(None), *filters)
                .group_by(column, Audit.ref)
            )

        union_agg = union_all(
            agg_query("MAIN CLAUSE", NCR.main_clause),
            agg_query("SUB CLAUSE", NCR.sub_clause),
            agg_query("SUB-SUB CLAUSE", NCR.ss_clause),
        ).subquery()

        agg_rows = (
            await self.session.execute(
                select(
                    union_agg.c.ctype,
                    union_agg.c.cvalue,
                    union_agg.c.audit_ref,
                    union_agg.c.cnt,
                )
            )
        ).all()

        for ctype, clause, audit_ref, count in agg_rows:
            key = (ctype, clause)
            if key in master:
                for bucket in master[key]:
                    if bucket["audit_ref"] == audit_ref:
                        bucket["count"] = count
                        break

        ncr_team = aliased(NCRTeam)
        creator = aliased(User)

        def detail_query(label, column):
            return (
                select(
                    literal(label).label("ctype"),
                    column.label("cvalue"),
                    Audit.ref.label("audit_ref"),
                    NCR.ref,
                    NCR.created_at,
                    creator.name.label("created_by"),
                    NCR.description,
                    NCR.status,
                )
                .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
                .join(Audit, AuditInfo.audit_id == Audit.id)
                .join(Plant, Audit.plant_id == Plant.id)
                .outerjoin(
                    ncr_team,
                    and_(
                        ncr_team.ncr_id == NCR.id,
                        ncr_team.role == NCRTeamRole.CREATED_BY,
                    ),
                )
                .outerjoin(creator, creator.id == ncr_team.user_id)
                .where(column.isnot(None), *filters)
            )

        detail_union = union_all(
            detail_query("MAIN CLAUSE", NCR.main_clause),
            detail_query("SUB CLAUSE", NCR.sub_clause),
            detail_query("SUB-SUB CLAUSE", NCR.ss_clause),
        )

        detail_rows = (await self.session.execute(detail_union)).all()

        for (
            ctype,
            clause,
            audit_ref,
            ref,
            created_at,
            created_by,
            desc,
            status,
        ) in detail_rows:
            key = (ctype, clause)
            if key in master:
                for bucket in master[key]:
                    if bucket["audit_ref"] == audit_ref:
                        bucket["ncr"].append(
                            {
                                "ref": ref,
                                "created_at": created_at,
                                "created_by": created_by,
                                "description": desc,
                                "status": status,
                            }
                        )
                        break

        result = {t: [] for t in CLAUSE_TYPES}

        for (ctype, clause), data in master.items():
            result[ctype].append(
                {
                    "clause": clause,
                    "data": data,
                }
            )

        return result

    async def get_clause_ncr_stats_department_wise(
        self,
        plant_id: Optional[UUID] = None,
        audit_id: Optional[UUID] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
    ):
        CLAUSE_TYPES = ["MAIN CLAUSE", "SUB CLAUSE", "SUB-SUB CLAUSE"]

        filters = []

        if created_from:
            filters.append(NCR.created_at >= to_naive(created_from))

        if created_to:
            filters.append(NCR.created_at <= to_naive(created_to))

        if plant_id:
            filters.append(Plant.id == plant_id)

        if audit_id:
            filters.append(Audit.id == audit_id)

        dept_rows = (
            await self.session.execute(
                select(Department.id, Department.name)
                .join(AuditInfo, AuditInfo.department_id == Department.id)
                .join(Audit, AuditInfo.audit_id == Audit.id)
                .join(Plant, Audit.plant_id == Plant.id)
                .where(
                    *([Plant.id == plant_id] if plant_id else []),
                    *([Audit.id == audit_id] if audit_id else []),
                )
                .distinct()
            )
        ).all()

        departments = [
            {"department_id": did, "department_name": name} for did, name in dept_rows
        ]

        clause_rows = (
            await self.session.execute(select(NCRClauses.clause, NCRClauses.type))
        ).all()

        master: dict = {}

        for clause, raw_type in clause_rows:
            if not clause or not raw_type:
                continue

            ctype = self.CLAUSE_TYPE_MAP.get(raw_type)
            if not ctype:
                continue

            master[(ctype, clause)] = [
                {
                    "department_id": d["department_id"],
                    "department_name": d["department_name"],
                    "count": 0,
                    "ncr": [],
                }
                for d in departments
            ]

        def agg_query(label, column):
            return (
                select(
                    literal(label).label("ctype"),
                    column.label("cvalue"),
                    Department.id.label("department_id"),
                    func.count(NCR.id).label("cnt"),
                )
                .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
                .join(Department, AuditInfo.department_id == Department.id)
                .join(Audit, AuditInfo.audit_id == Audit.id)
                .join(Plant, Audit.plant_id == Plant.id)
                .where(column.isnot(None), *filters)
                .group_by(column, Department.id)
            )

        union_agg = union_all(
            agg_query("MAIN CLAUSE", NCR.main_clause),
            agg_query("SUB CLAUSE", NCR.sub_clause),
            agg_query("SUB-SUB CLAUSE", NCR.ss_clause),
        ).subquery()

        agg_rows = (
            await self.session.execute(
                select(
                    union_agg.c.ctype,
                    union_agg.c.cvalue,
                    union_agg.c.department_id,
                    union_agg.c.cnt,
                )
            )
        ).all()

        for raw_type, clause, dept_id, count in agg_rows:
            ctype = self.CLAUSE_TYPE_MAP.get(raw_type)
            if not ctype:
                continue

            key = (ctype, clause)
            if key in master:
                for bucket in master[key]:
                    if bucket["department_id"] == dept_id:
                        bucket["count"] = count
                        break

        ncr_team = aliased(NCRTeam)
        creator = aliased(User)

        def detail_query(label, column):
            return (
                select(
                    literal(label).label("ctype"),
                    column.label("cvalue"),
                    Department.id.label("department_id"),
                    NCR.ref,
                    NCR.created_at,
                    creator.name.label("created_by"),
                    NCR.description,
                    NCR.status,
                )
                .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
                .join(Department, AuditInfo.department_id == Department.id)
                .join(Audit, AuditInfo.audit_id == Audit.id)
                .join(Plant, Audit.plant_id == Plant.id)
                .outerjoin(
                    ncr_team,
                    and_(
                        ncr_team.ncr_id == NCR.id,
                        ncr_team.role == NCRTeamRole.CREATED_BY,
                    ),
                )
                .outerjoin(creator, creator.id == ncr_team.user_id)
                .where(column.isnot(None), *filters)
            )

        detail_union = union_all(
            detail_query("MAIN CLAUSE", NCR.main_clause),
            detail_query("SUB CLAUSE", NCR.sub_clause),
            detail_query("SUB-SUB CLAUSE", NCR.ss_clause),
        )

        detail_rows = (await self.session.execute(detail_union)).all()

        for (
            raw_type,
            clause,
            dept_id,
            ref,
            created_at,
            created_by,
            desc,
            status,
        ) in detail_rows:
            ctype = self.CLAUSE_TYPE_MAP.get(raw_type)
            if not ctype:
                continue

            key = (ctype, clause)
            if key in master:
                for bucket in master[key]:
                    if bucket["department_id"] == dept_id:
                        bucket["ncr"].append(
                            {
                                "ref": ref,
                                "created_at": created_at,
                                "created_by": created_by,
                                "description": desc,
                                "status": status,
                            }
                        )
                        break

        result = {t: [] for t in CLAUSE_TYPES}

        for (ctype, clause), data in master.items():
            result[ctype].append(
                {
                    "clause": clause,
                    "data": data,
                }
            )

        final_response = {
            "MAIN CLAUSE": [],
            "SUB CLAUSE": [],
            "SUB-SUB CLAUSE": [],
        }

        for (ctype, clause), data in master.items():
            final_response[ctype].append(
                {
                    "clause": clause,
                    "data": data,
                }
            )

        return final_response

    def empty_status_counts(self) -> dict[str, int]:
        return {status: 0 for status in self.ALL_NCR_STATUSES}

    def apply_common_filters(
        self,
        stmt,
        company_id: UUID | None = None,
        plant_id: UUID | None = None,
        audit_id: UUID | None = None,
        department_id: UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        if company_id:
            stmt = stmt.where(Company.id == company_id)
        if plant_id:
            stmt = stmt.where(Plant.id == plant_id)
        if audit_id:
            stmt = stmt.where(Audit.id == audit_id)
        if department_id:
            stmt = stmt.where(Department.id == department_id)
        if from_date:
            stmt = stmt.where(NCR.created_at >= to_naive(from_date))
        if to_date:
            stmt = stmt.where(NCR.created_at <= to_naive(to_date))
        return stmt

    def ncr_to_dict(self, ncr: NCR) -> dict:
        return {
            "id": ncr.id,
            "ref": ncr.ref,
            "status": ncr.status,
            "type": ncr.type,
            "repeat": ncr.repeat,
            "expected_date_of_completion": ncr.expected_date_of_completion,
            "actual_date_of_completion": ncr.actual_date_of_completion,
            "closed_on": ncr.closed_on,
        }

    async def get_department_status_counts(
        self,
        company_id: UUID | None = None,
        plant_id: UUID | None = None,
        audit_id: UUID | None = None,
        department_id: UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[dict]:

        dept_stmt = (
            select(Department.id, Department.name)
            .join(AuditInfo, AuditInfo.department_id == Department.id)
            .join(Audit, AuditInfo.audit_id == Audit.id)
            .join(Plant, Audit.plant_id == Plant.id)
            .join(Company, Plant.company_id == Company.id)
            .distinct()
        )

        dept_stmt = self.apply_common_filters(
            dept_stmt,
            company_id=company_id,
            plant_id=plant_id,
            audit_id=audit_id,
            department_id=department_id,
            from_date=from_date,
            to_date=to_date,
        )

        dept_rows = (await self.session.execute(dept_stmt)).all()

        result: dict[UUID, dict] = {
            dept_id: {
                "id": dept_id,
                "name": dept_name,
                "status_counts": self.empty_status_counts(),
                "ncrs": [],
            }
            for dept_id, dept_name in dept_rows
        }

        count_stmt = (
            select(
                Department.id.label("department_id"),
                NCR.status,
                func.count(NCR.id),
            )
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .join(Department, AuditInfo.department_id == Department.id)
            .join(Audit, AuditInfo.audit_id == Audit.id)
            .join(Plant, Audit.plant_id == Plant.id)
            .join(Company, Plant.company_id == Company.id)
            .group_by(Department.id, NCR.status)
        )

        count_stmt = self.apply_common_filters(
            count_stmt,
            company_id=company_id,
            plant_id=plant_id,
            audit_id=audit_id,
            department_id=department_id,
            from_date=from_date,
            to_date=to_date,
        )

        for dept_id, status, count in (await self.session.execute(count_stmt)).all():
            result[dept_id]["status_counts"][status] = count

        ncr_stmt = (
            select(NCR, Department.id)
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .join(Department, AuditInfo.department_id == Department.id)
            .join(Audit, AuditInfo.audit_id == Audit.id)
            .join(Plant, Audit.plant_id == Plant.id)
            .join(Company, Plant.company_id == Company.id)
        )

        ncr_stmt = self.apply_common_filters(
            ncr_stmt,
            company_id=company_id,
            plant_id=plant_id,
            audit_id=audit_id,
            department_id=department_id,
            from_date=from_date,
            to_date=to_date,
        )

        for ncr, dept_id in (await self.session.execute(ncr_stmt)).all():
            result[dept_id]["ncrs"].append(self.ncr_to_dict(ncr))

        return list(result.values())

    async def get_plant_status_counts(
        self,
        company_id: UUID | None = None,
        plant_id: UUID | None = None,
        audit_id: UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[dict]:

        plant_stmt = (
            select(Plant.id, Plant.name)
            .join(Audit, Audit.plant_id == Plant.id)
            .join(AuditInfo, AuditInfo.audit_id == Audit.id)
            .join(NCR, NCR.audit_info_id == AuditInfo.id)
            .join(Company, Plant.company_id == Company.id)
            .distinct()
        )

        plant_stmt = self.apply_common_filters(
            plant_stmt,
            company_id=company_id,
            from_date=to_naive(from_date),
            to_date=to_naive(to_date),
        )

        plant_rows = (await self.session.execute(plant_stmt)).all()

        result: dict[UUID, dict] = {
            p_id: {
                "id": p_id,
                "name": p_name,
                "status_counts": self.empty_status_counts(),
                "ncrs": [],
            }
            for p_id, p_name in plant_rows
        }

        count_stmt = (
            select(
                Plant.id,
                NCR.status,
                func.count(NCR.id),
            )
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .join(Audit, AuditInfo.audit_id == Audit.id)
            .join(Plant, Audit.plant_id == Plant.id)
            .join(Company, Plant.company_id == Company.id)
            .group_by(Plant.id, NCR.status)
        )

        count_stmt = self.apply_common_filters(
            count_stmt,
            company_id=company_id,
            plant_id=plant_id,
            audit_id=audit_id,
            from_date=from_date,
            to_date=to_date,
        )

        for p_id, status, count in (await self.session.execute(count_stmt)).all():
            result[p_id]["status_counts"][status] = count

        ncr_stmt = (
            select(NCR, Plant.id)
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .join(Audit, AuditInfo.audit_id == Audit.id)
            .join(Plant, Audit.plant_id == Plant.id)
            .join(Company, Plant.company_id == Company.id)
        )

        ncr_stmt = self.apply_common_filters(
            ncr_stmt,
            company_id=company_id,
            plant_id=plant_id,
            audit_id=audit_id,
            from_date=from_date,
            to_date=to_date,
        )

        for ncr, p_id in (await self.session.execute(ncr_stmt)).all():
            result[p_id]["ncrs"].append(self.ncr_to_dict(ncr))

        return list(result.values())

    async def get_company_status_counts(
        self,
        company_id: UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[dict]:

        company_stmt = select(Company.id, Company.name)
        if company_id:
            company_stmt = company_stmt.where(Company.id == company_id)

        company_rows = (await self.session.execute(company_stmt)).all()

        result: dict[UUID, dict] = {
            c_id: {
                "id": c_id,
                "name": c_name,
                "status_counts": self.empty_status_counts(),
                "ncrs": [],
            }
            for c_id, c_name in company_rows
        }

        count_stmt = (
            select(
                Company.id,
                NCR.status,
                func.count(NCR.id),
            )
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .join(Audit, AuditInfo.audit_id == Audit.id)
            .join(Plant, Audit.plant_id == Plant.id)
            .join(Company, Plant.company_id == Company.id)
            .group_by(Company.id, NCR.status)
        )

        count_stmt = self.apply_common_filters(
            count_stmt,
            company_id=company_id,
            from_date=from_date,
            to_date=to_date,
        )

        for c_id, status, count in (await self.session.execute(count_stmt)).all():
            result[c_id]["status_counts"][status] = count

        ncr_stmt = (
            select(NCR, Company.id)
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .join(Audit, AuditInfo.audit_id == Audit.id)
            .join(Plant, Audit.plant_id == Plant.id)
            .join(Company, Plant.company_id == Company.id)
        )

        ncr_stmt = self.apply_common_filters(
            ncr_stmt,
            company_id=company_id,
            from_date=from_date,
            to_date=to_date,
        )

        for ncr, c_id in (await self.session.execute(ncr_stmt)).all():
            result[c_id]["ncrs"].append(self.ncr_to_dict(ncr))

        return list(result.values())
