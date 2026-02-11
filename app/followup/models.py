

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from app.core.schemas import BaseModel

class FollowupStatus(str, Enum):
    NONASSIGNED = "NONASSIGNED"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"


class Followup(BaseModel, table=True):
    requested_date: datetime = Field(default_factory=datetime.now)
    status: str = Field(default=FollowupStatus.NONASSIGNED)
    ncr_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("ncr.id", ondelete="CASCADE"), nullable=False
        )
    )
     
    ncr: "NCR" = Relationship(back_populates="followup")
    observations: Optional[str] = None
    assgined_on: datetime = Field(default_factory=datetime.now)
    completed_on: datetime = Field(default_factory=datetime.now)
    auditor_id: Optional[UUID] = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=True
        )
    )
    auditor:  Optional["User"] = Relationship(back_populates="followup_auditor",sa_relationship_kwargs={
        "foreign_keys": "Followup.auditor_id",
    })
    requested_by_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        )
    )
    requested_by: "User" = Relationship(back_populates="requested_followup",sa_relationship_kwargs={
            "foreign_keys": "Followup.requested_by_id"
        },)
    
    
class CreateFollowupRequest(PydanticBaseModel):
    ncr_id: UUID
    
class UpdateFollowupRequest(PydanticBaseModel):
    auditor_id: UUID | None = None
    completed_on: datetime | None = None
    observations : Optional[str] = None
    
class FollowupResponse(PydanticBaseModel):
    id: UUID
    requested_date: datetime
    status: str
    ncr_id: UUID
    auditor_id: Optional[UUID] = None
    auditor: Optional["UserResponse"] = None
    observations : Optional[str] = None
    requested_by_id: Optional[UUID] = None
    assgined_on: datetime
    completed_on: datetime
    requested_by: Optional["UserResponse"] = None
    ncr: "NCRResponse" = None
    created_at : datetime
    
    
class FollowupListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data : list["FollowupResponse"] = []

    
from app.users.models import User, UserResponse
from app.ncr.models import NCR, NCRResponse
