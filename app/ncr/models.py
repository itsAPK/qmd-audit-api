

from pydantic import BaseModel as PydanticBaseModel,RootModel
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship
from app.core.schemas import BaseModel
from sqlalchemy.dialects.postgresql import UUID as PG_UUID




class NCRStatus(str, Enum):
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    FOLLOW_COMPLETED = "FOLLOW_COMPLETED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    FOLLOWUP_REQUESTED = "FOLLOWUP_REQUESTED"
    FOLLOW_ASSIGNED = "FOLLOW_ASSIGNED"
    
    
class NCRMode(str, Enum):
    NCR = "NCR"
    SUGGESTION = "SUGGESTION"
    
class NCRShift(BaseModel, table=True):
    name : str
    
class NCRTeamRole(str, Enum):
    CREATED_BY = "CREATED_BY"
    HOD = "HOD"
    FOLLOWUP_AUDITOR = "FOLLOWUP_AUDITOR"
    AUDITEE = "AUDITEE"
    
class NCRTeam(BaseModel, table=True):
    user_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        )
    )
    user: "User" = Relationship(back_populates="ncr_teams")
    ncr_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("ncr.id", ondelete="CASCADE"), nullable=False
        )
    )
    ncr: "NCR" = Relationship(back_populates="team")
    role : NCRTeamRole = Field(default=NCRTeamRole.CREATED_BY)
    
class NCRFileType(str, Enum):
    NCR_FILE = "NCR_FILE"
    FOLLOWUP_FILE = "FOLLOWUP_FILE"
    
class NCRFiles(BaseModel, table=True):
        ncr_id : UUID = Field(
            sa_column=Column(
                PG_UUID, ForeignKey("ncr.id", ondelete="CASCADE"), nullable=False
            )
        )
        ncr: "NCR" = Relationship(back_populates="files")
        path: str 
        file_type: NCRFileType
    
class NCR(BaseModel, table=True):
    ref: str
    status: NCRStatus = Field(default=NCRStatus.CREATED)
    mode : NCRMode = Field(default=NCRMode.NCR)
    shift : str
    type : str
    repeat : bool = Field(default=False)
    audit_info_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("auditinfo.id", ondelete="CASCADE"), nullable=False
        )
    )
    audit_info: "AuditInfo" = Relationship(back_populates="ncrs")
    description : Optional[str] = None
    objective_evidence : Optional[str] = None
    requirement : Optional[str] = None
    correction : Optional[str] = None
    root_cause : Optional[str] = None
    systematic_corrective_action : Optional[str] = None
    corrective_action_details : Optional[str] = None
    expected_date_of_completion : Optional[datetime] = None
    actual_date_of_completion : Optional[datetime] = None
    edc_given_date : Optional[datetime] = None
    remarks : Optional[str] = None
    followup_observations : Optional[str] = None
    followup_date : Optional[datetime] = None
    rejected_reson : Optional[str] = None
    rejected_count : Optional[int] = Field(default=0)
    closed_on : Optional[datetime] = None
    main_clause : Optional[str] = None
    sub_clause : Optional[str] = None
    ss_clause : Optional[str] = None
    document_references : list["DocumentReference"] = Relationship(
        back_populates="ncr",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    team : list["NCRTeam"] = Relationship(
        back_populates="ncr",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    files : list["NCRFiles"] = Relationship(
        back_populates="ncr",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    followup : list["Followup"] = Relationship(
        back_populates="ncr",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
)
    edc_requests : list["EdcRequest"] = Relationship(
        back_populates="ncr",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

class DocumentReference(BaseModel, table=True):
        ref: str
        page: str
        paragraph: str
        ncr_id : UUID = Field(
            sa_column=Column(
                PG_UUID, ForeignKey("ncr.id", ondelete="CASCADE"), nullable=False
            )
        )
        ncr: "NCR" = Relationship(back_populates="document_references")
        
        
class NCRClauseType(str, Enum):
    MAIN = "MAIN CLAUSE"
    SUB = "SUB CLAUSE"
    SS = "SUB-SUB CLAUSE"
        
class NCRClauses(BaseModel, table=True):
    clause : str
    type : NCRClauseType = Field(default=NCRClauseType.MAIN)
    

class NCRClausesRequest(PydanticBaseModel):
    clause : str
    type : NCRClauseType = Field(default=NCRClauseType.MAIN)
    
    
class NCRShiftCreateRequest(PydanticBaseModel):
    name: str
    
    
class DocumentReferenceRequest(PydanticBaseModel):
    ref: str
    page: str
    paragraph: str
    
class NCRCreateRequest(PydanticBaseModel):
    mode : Optional[str]  = NCRMode.NCR
    auditee_id : UUID
    shift : str
    type : str
    repeat : Optional[bool] = False
    audit_info_id : UUID 
    description : Optional[str] = None
    objective_evidence : Optional[str] = None
    requirement : Optional[str] = None
    main_clause : Optional[str] = None
    sub_clause : Optional[str] = None
    ss_clause : Optional[str] = None
    document_references : list["DocumentReferenceRequest"] = []
    
class NCRUpdateRequest(PydanticBaseModel):
   auditee_id : Optional[UUID] = None
   shift : Optional[str] = None
   type : Optional[str] = None
   repeat : Optional[bool] = None
   audit_info_id : Optional[UUID] = None
   description : Optional[str] = None
   objective_evidence : Optional[str] = None
   requirement : Optional[str] = None
   main_clause : Optional[str] = None
   sub_clause : Optional[str] = None
   ss_clause : Optional[str] = None
   correction : Optional[str] = None
   root_cause : Optional[str] = None
   systematic_corrective_action : Optional[str] = None
   corrective_action_details : Optional[str] = None
   expected_date_of_completion : Optional[datetime] = None
   actual_date_of_completion : Optional[datetime] = None
   edc_given_date : Optional[datetime] = None
   remarks : Optional[str] = None
   followup_observations : Optional[str] = None
   followup_date : Optional[datetime] = None
   rejected_reson : Optional[str] = None
   rejected_count : Optional[int] = None
   closed_on : Optional[datetime] = None
   document_references : list["DocumentReferenceRequest"] = []
   status : Optional[NCRStatus] = None
    

class NCRTeamCreateRequest(PydanticBaseModel):
    user_id : UUID
    role : NCRTeamRole
    ncr_id : UUID
    
class NCRTeamUpdateRequest(PydanticBaseModel):
    user_id : Optional[UUID] = None
    role_id : Optional[NCRTeamRole] = None
    
    
class NCRTeamResponse(PydanticBaseModel):
    id: UUID
    user_id : UUID
    role : NCRTeamRole
    ncr_id : UUID
    user : Optional["UserResponse"] = None
    
    
    
class CreateDocumentReferenceRequest(PydanticBaseModel):
        ref: str
        page: str
        paragraph: str

    
class NCRResponse(PydanticBaseModel):
    id: UUID
    ref: str
    mode : str
    shift : str
    type : str
    status : NCRStatus
    repeat : bool
    audit_info_id : UUID
    created_at : Optional[datetime] = None
    description : Optional[str] = None
    objective_evidence : Optional[str] = None
    requirement : Optional[str] = None
    main_clause : Optional[str] = None
    sub_clause : Optional[str] = None
    ss_clause : Optional[str] = None
    correction : Optional[str] = None
    root_cause : Optional[str] = None
    systematic_corrective_action : Optional[str] = None
    corrective_action_details : Optional[str] = None
    expected_date_of_completion : Optional[datetime] = None
    actual_date_of_completion : Optional[datetime] = None
    edc_given_date : Optional[datetime] = None
    remarks : Optional[str] = None
    followup_observations : Optional[str] = None
    followup_date : Optional[datetime] = None
    rejected_reson : Optional[str] = None
    rejected_count : Optional[int] = None
    closed_on : Optional[datetime] = None
    main_clause : Optional[str] = None
    sub_clause : Optional[str] = None
    ss_clause : Optional[str] = None
    document_references : list["DocumentReference"] = []
    team : list["NCRTeamResponse"] = []
    audit_info: Optional["AuditInfoResponse"] = None
    files : list["NCRFiles"] = []
    
    
    
    

class NCRListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data : list["NCRResponse"] = []
    
class NCRDetail(PydanticBaseModel):
    ref: str
    created_at: datetime
    created_by: Optional[str]
    description: Optional[str]
    status: NCRStatus


class AuditBucket(PydanticBaseModel):
    audit_ref: str
    count: int
    ncr: List[NCRDetail]


class ClauseGroup(PydanticBaseModel):
    clause: str
    data: List[AuditBucket]


class ClauseNCRStatsResponse(PydanticBaseModel):
    main_clause: List[ClauseGroup] = Field(alias="MAIN CLAUSE")
    sub_clause: List[ClauseGroup] = Field(alias="SUB CLAUSE")
    sub_sub_clause: List[ClauseGroup] = Field(alias="SUB-SUB CLAUSE")

    class Config:
        populate_by_name = True
        
        
class DepartmentBase(PydanticBaseModel):
    department_id : UUID
    department_name : str
    count : int
    ncr : List[NCRDetail]
    
    
class DepartmentWiseNCRResponse(PydanticBaseModel):
    clause : str
    data : List[DepartmentBase]
        
        
class DepartmentWiseNCRStatsResponse(PydanticBaseModel):
    main_clause: List[DepartmentWiseNCRResponse] = Field(alias="MAIN CLAUSE")
    sub_clause: List[DepartmentWiseNCRResponse] = Field(alias="SUB CLAUSE")
    sub_sub_clause: List[DepartmentWiseNCRResponse] = Field(alias="SUB-SUB CLAUSE")

    class Config:    
        populate_by_name = True


class NCRListItem(BaseModel):
    id: UUID
    ref: str
    status: NCRStatus
    type: str
    repeat: bool
    expected_date_of_completion: Optional[datetime] = None
    actual_date_of_completion: Optional[datetime]  = None
    closed_on: Optional[datetime]  = None

    model_config = {
        "use_enum_values": True
    }

class NCRStatusResponse(PydanticBaseModel):
    id: UUID
    name: str
    status_counts: Dict[NCRStatus, int]
    ncrs: List[NCRListItem]

    class Config:
        use_enum_values = True


from app.audit_info.models import AuditInfo, AuditInfoResponse
from app.users.models import User, UserResponse
from app.followup.models import Followup
from app.edc_request.models import EdcRequest
