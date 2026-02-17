
from pydantic import BaseModel as PydanticBaseModel,RootModel
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship
from app.core.schemas import BaseModel
from sqlalchemy.dialects.postgresql import UUID as PG_UUID




class SuggestionTeamRole(str, Enum):
    CREATED_BY = "CREATED_BY"
    HOD = "HOD"
    AUDITEE = "AUDITEE"
    
class SuggestionStatus(str, Enum):
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    
class SuggestionTeam(BaseModel, table=True):
    user_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        )
    )
    user: "User" = Relationship(back_populates="suggestion_teams")
    suggestion_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("suggestion.id", ondelete="CASCADE"), nullable=False
        )
    )
    suggestion: "Suggestion" = Relationship(back_populates="team")
    role : SuggestionTeamRole = Field(default=SuggestionTeamRole.CREATED_BY)
    

class Suggestion(BaseModel,table=True):
    ref: str
    status: SuggestionStatus = Field(default=SuggestionStatus.CREATED)
    audit_info_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("auditinfo.id", ondelete="CASCADE"), nullable=False
        )
    )
    audit_info: "AuditInfo" = Relationship(back_populates="suggestions")
    expected_date_of_completion : Optional[datetime] = None
    actual_date_of_completion : Optional[datetime] = None
    suggestion: str
    corrective_action : Optional[str] = None
    team : list["SuggestionTeam"] = Relationship(
        back_populates="suggestion",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    
    
class SuggestionCreateRequest(PydanticBaseModel):
    audit_info_id : UUID
    suggestion: str

class SuggestionUpdateRequest(PydanticBaseModel):
    audit_info_id : Optional[UUID] = None
    suggestion: Optional[str] = None
    corrective_action : Optional[str] = None
    status : Optional[SuggestionStatus] = None
    expected_date_of_completion : Optional[datetime] = None
    actual_date_of_completion : Optional[datetime] = None
    created_at : Optional[datetime] = None
    
class SuggestionTeamCreateRequest(PydanticBaseModel):
   user_id: UUID
   role: SuggestionTeamRole
   suggestion_id : UUID
    
class SuggestionTeamResponse(PydanticBaseModel):
    id: UUID
    user_id : UUID
    role : SuggestionTeamRole
    ncr_id : UUID
    user : Optional["UserResponse"] = None
    
    
class SuggestionResponse(PydanticBaseModel):
    id: UUID
    ref: str
    status: SuggestionStatus
    audit_info_id : UUID
    expected_date_of_completion : Optional[datetime] = None
    actual_date_of_completion : Optional[datetime] = None
    suggestion: str
    corrective_action : Optional[str] = None
    audit_info: Optional["AuditInfoResponse"] = None
    team: list["SuggestionTeamResponse"] = []
    created_at : datetime
    
class SuggestionListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data : list["SuggestionResponse"] = []
    
    
from app.users.models import User, UserResponse
from app.audit_info.models import AuditInfo, AuditInfoResponse
