
from enum import Enum
from typing import Optional
from sqlmodel import Field, Relationship
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from app.core.schemas import BaseModel
from pydantic import BaseModel as PydanticBaseModel
from datetime import datetime

class EDCStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class EdcRequest(BaseModel, table=True):
    ncr_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("ncr.id", ondelete="CASCADE"), nullable=False
        )
    )
    
    requested_by_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        )
    )
    requested_by: "User" = Relationship(back_populates="requested_edc_requests",sa_relationship_kwargs={
            "foreign_keys": "EdcRequest.requested_by_id"
        },)
    
    ncr: "NCR" = Relationship(back_populates="edc_requests")
    new_edc : datetime
    old_edc : datetime
    comment : str
    status : EDCStatus = Field(default=EDCStatus.PENDING)
    
class CreateEdcRequestRequest(PydanticBaseModel):
    ncr_id: UUID
    new_edc : datetime
    comment : str
    
class UpdateEDCRequestRequest(PydanticBaseModel):
    old_edc : Optional[datetime] = None
    new_edc : Optional[datetime] = None
    comment : Optional[str] = None
    status : Optional[EDCStatus] = None
    
class EdcRequestResponse(PydanticBaseModel):
    id: UUID
    ncr_id: UUID
    requested_by_id: UUID
    new_edc : datetime
    old_edc : datetime
    comment : str
    status : EDCStatus
    ncr: "NCRResponse" = None
    created_at : datetime
    requested_by: "UserResponse" = None
    
class EdcRequestListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data : list["EdcRequestResponse"] = []
    
from app.users.models import User, UserResponse
from app.ncr.models import NCR, NCRResponse
