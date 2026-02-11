

from datetime import datetime
from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from app.core.schemas import BaseModel
from enum import Enum
from pydantic import BaseModel as PydanticBaseModel
from typing import Dict, Optional



class AuditInfoStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class AuditInfo(BaseModel, table=True):
    ref: str
    department_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("department.id", ondelete="CASCADE"), nullable=False
        )
    )
    department:  "Department" = Relationship(back_populates="audits")
    from_date: datetime = Field(default_factory=datetime.now)
    to_date: datetime = Field(default_factory=datetime.now)
    closed_date: Optional[datetime] = None
    status: AuditInfoStatus = Field(default=AuditInfoStatus.OPEN)
    team: list["AuditTeam"] = Relationship(
        back_populates="audit_info",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    audit_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("audit.id", ondelete="CASCADE"), nullable=False
        )
    )
    
    audit: "Audit" = Relationship(back_populates="audit_info")
    ncrs : list["NCR"] = Relationship(
        back_populates="audit_info",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    

class AuditTeamRole(str, Enum):
    AUDITOR = "AUDITOR"
    TRAINEE = "TRAINEE"
    AUDITEE_COORDINATOR = "AUDITEE_COORDINATOR"
    AUDITEE = "AUDITEE"
    


class AuditTeam(BaseModel, table=True):
    user_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        )
    )
    audit_info_id: Optional[UUID] = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("auditinfo.id", ondelete="CASCADE"), nullable=False
        )
    )
    role: AuditTeamRole = Field(default=AuditTeamRole.AUDITOR)
    
    user: "User" = Relationship(back_populates="audit_teams")
    audit_info: Optional["AuditInfo"] = Relationship(back_populates="team")
    
class AuditTeamRequest(PydanticBaseModel):
    user_id: UUID
    role: AuditTeamRole

class AuditInfoRequest(PydanticBaseModel):
    department_id: UUID
    from_date: datetime
    to_date: datetime
    status: AuditInfoStatus = AuditInfoStatus.OPEN
    team: list[AuditTeamRequest] = []
    audit_id : UUID
    

class AuditInfoUpdateRequest(PydanticBaseModel):
   closed_date: Optional[datetime] = None
   from_date: Optional[datetime] = None
   to_date: Optional[datetime] = None

    

class AuditTeamResponse(PydanticBaseModel):
    id: UUID
    user_id: UUID
    role: AuditTeamRole
    user: "UserResponse"
    
class AuditInfoResponse(PydanticBaseModel):
    id: UUID
    ref: str
    department_id: UUID
    department: Optional["DepartmentResponse"] = None
    from_date: datetime
    to_date: datetime
    closed_date: Optional[datetime] = None
    status: AuditInfoStatus
    team: list[AuditTeamResponse] = []
    audit : Optional["Audit"] = None
    ncr_status_count: Dict[str, int] = {}
    
    
class AuditInfoListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data : list["AuditInfoResponse"]
    
    
    
from app.audit.models import Audit
from app.settings.models import Department,DepartmentResponse
from app.users.models import User,UserResponse
from app.ncr.models import NCR
