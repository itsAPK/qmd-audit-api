from enum import Enum
from pydantic import BaseModel as PydanticBaseModel

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from enum import Enum
from typing import List, Optional
from uuid import UUID

from sqlalchemy import ARRAY, Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

from app.core.schemas import BaseModel


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class UserRole(BaseModel, table=True):
    role: str = Field(unique=True, nullable=False)
    description: str
    permissions: Optional[List[str]] = Field(
        default=None, sa_column=Column(ARRAY(String), nullable=True)
    )

    departments: List["UserDepartment"] = Relationship(
        back_populates="role",
    )


UserRole.model_rebuild()


class User(BaseModel, table=True):
    employee_id: str = Field(unique=True, nullable=False)
    name: str = Field(nullable=True)
    password: str = Field(nullable=False)
    email: str = Field(nullable=False)
    qualification: str
    designation: str
    is_active: bool = Field(default=True)
    role: RoleEnum = Field(default=RoleEnum.USER)

    departments: list["UserDepartment"] = Relationship(
        back_populates="user",
    )

    audit_teams: list["AuditTeam"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    ncr_teams: list["NCRTeam"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    followup_auditor: list["Followup"] = Relationship(
        back_populates="auditor",
        sa_relationship_kwargs={
            "foreign_keys": "Followup.auditor_id",
            "cascade": "all, delete-orphan",
        },
    )

    requested_followup: list["Followup"] = Relationship(
        back_populates="requested_by",
        sa_relationship_kwargs={
            "foreign_keys": "Followup.requested_by_id",
            "cascade": "all, delete-orphan",
        },
    )
    requested_edc_requests: list["EdcRequest"] = Relationship(
        back_populates="requested_by",
        sa_relationship_kwargs={
            "foreign_keys": "EdcRequest.requested_by_id",
            "cascade": "all, delete-orphan",
        },
    )

    franchise_audit_checklists: List["FranchiseAuditChecklist"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    brcp_warehouse_checklists: List["BRCPWarehouseChecklist"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    internal_audit_observation_checklists: List["InternalAuditObservationChecklist"] = (
        Relationship(
            back_populates="created_by",
            sa_relationship_kwargs={"cascade": "all, delete-orphan"},
        )
    )

    internal_auditors_checklists: List["InternalAuditorsChecklist"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


User.model_rebuild()


class RoleRequest(PydanticBaseModel):
    role: str
    description: str
    permissions: Optional[List[str]] = None


class RoleUpdateRequest(PydanticBaseModel):
    role: str | None = None
    description: str | None = None
    permissions: Optional[List[str]] = None


class RolesResponseList(PydanticBaseModel):
    roles: list["RoleResponse"] = []


class UserCreateRequest(PydanticBaseModel):
    employee_id: str
    password: str
    email: str
    qualification: str
    designation: str
    role: RoleEnum
    name: str


class UpdateUserRequest(PydanticBaseModel):
    employee_id: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    qualification: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[RoleEnum] = None
    name: Optional[str] = None


class UserDepartmentResponse(PydanticBaseModel):
    id: UUID
    user_id: UUID
    department_id: UUID
    role_id: UUID
    department: Optional["Department"] = None
    role: Optional["UserRole"] = None
    user: Optional["User"] = None


class RoleResponse(PydanticBaseModel):
    id: UUID
    role: str
    description: str
    permissions: Optional[List[str]] = None
    users: list["UserDepartmentResponse"] = []


class UserResponse(PydanticBaseModel):
    id: UUID
    employee_id: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None
    qualification: Optional[str] = None
    designation: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    name: Optional[str] = None
    departments: list["UserDepartmentResponse"] = []


class UserListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data: list["UserResponse"] = []


class AssignUserDepartmentRequest(PydanticBaseModel):
    user_id: UUID
    department_id: UUID
    role_id: UUID


class RemoveUserDepartmentRequest(PydanticBaseModel):
    user_id: UUID
    department_id: UUID


from app.ncr.models import NCRTeam
from app.settings.models import Department
from app.settings.links import UserDepartment
from app.audit_info.models import AuditTeam
from app.followup.models import Followup

from app.edc_request.models import EdcRequest

from app.checklist.models import (
    BRCPWarehouseChecklist,
    InternalAuditorsChecklist,
    InternalAuditObservationChecklist,
    FranchiseAuditChecklist,
)
