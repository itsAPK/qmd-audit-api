


from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, Relationship
from app.core.schemas import BaseModel
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID




class AuditSchedule(BaseModel, table=True):
    name: str
    
class AuditType(BaseModel, table=True):
    name: str
    code : str
    
class AuditStandard(BaseModel, table=True):
    name: str
    
class AuditSettingsRequest(PydanticBaseModel):
    name: str
    
class AuditTypeRequest(PydanticBaseModel):
    name: str
    code : str

class Audit(BaseModel, table=True):
    ref: str
    type: str
    standard: str
    schedule: str
    start_date: datetime = Field(default_factory=datetime.now)
    end_date: datetime = Field(default_factory=datetime.now)
    remarks: Optional[str] = None
    plant_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("plant.id", ondelete="CASCADE"), nullable=False
        )
    )
    plant: "Plant" = Relationship(back_populates="audits")
    audit_info: list["AuditInfo"] = Relationship(
        back_populates="audit",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    
    
    
    
class AuditRequest(PydanticBaseModel):
    type: str
    standard: str
    schedule: str
    start_date: datetime
    end_date: datetime
    remarks: Optional[str] = None
    department_id: UUID
    
class AuditUpdateRequest(PydanticBaseModel):
   type: Optional[str] = None
   standard: Optional[str] = None
   schedule: Optional[str] = None
   start_date: Optional[datetime] = None
   end_date: Optional[datetime] = None
   remarks: Optional[str] = None
    
    
class AuditResponse(PydanticBaseModel):
    id: UUID
    ref: str
    type: str
    standard: str
    schedule: str
    start_date: datetime
    end_date: datetime
    remarks: Optional[str] = None
    plant_id: Optional[UUID] = None
    plant: Optional["PlantResponse"] = None
    
    
    
class AuditListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data: List["AuditResponse"]
    
    
class AuditIdResponse(PydanticBaseModel):
        id: UUID
        ref: str
    
from app.settings.models import Plant, PlantResponse
from app.audit_info.models import AuditInfo
