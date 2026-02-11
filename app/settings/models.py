from typing import List, Optional
from app.core.schemas import BaseModel
from sqlalchemy import ARRAY, Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from pydantic import BaseModel as PydanticBaseModel


class Company(BaseModel, table=True):
    name: str
    code: str
    plants: List["Plant"] = Relationship(
        back_populates="company",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Plant(BaseModel, table=True):
    name: str
    code: str
    company_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("company.id", ondelete="CASCADE"), nullable=False
        )
    )
    company: Company = Relationship(back_populates="plants")
    departments: List["Department"] = Relationship(
        back_populates="plant", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    audits: List["Audit"] = Relationship(
        back_populates="plant", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

Plant.model_rebuild()

class Department(BaseModel, table=True):
    name: str
    code: str
    slug: str

    plant_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("plant.id", ondelete="CASCADE"), nullable=False
        )
    )

    plant: "Plant" = Relationship(back_populates="departments")

    users: list["UserDepartment"] = Relationship(
        back_populates="department"
    )
    
    audits : list["AuditInfo"] = Relationship(
        back_populates="department",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    

class CompanyRequest(PydanticBaseModel):
    name: str
    code: str
    
class DepartmentRequest(PydanticBaseModel):
    name: str
    code: str
    plant_id: UUID
    
class PlantRequest(PydanticBaseModel):
    name: str
    code: str
    company_id: UUID
    
class CompanyUpdateRequest(PydanticBaseModel):
    name: str | None = None
    code: str | None = None
    
class PlantUpdateRequest(PydanticBaseModel):
    name: str | None = None
    code: str | None = None
    company_id: UUID | None = None

class DepartmentUpdateRequest(PydanticBaseModel):
    name: str | None = None
    code: str | None = None
    plant_id: UUID | None = None

class CompanyResponse(PydanticBaseModel):
    id: UUID
    name: str
    code: str
    plants: List["PlantResponse"] = []

class PlantResponse(PydanticBaseModel):
    id: UUID
    name: str
    code: str
    company_id: UUID
    company: Optional[CompanyResponse] = None
    departments: List["DepartmentResponse"] = []

class DepartmentResponse(PydanticBaseModel):
    id: UUID
    name: str
    code: str
    slug: str
    plant_id: Optional[UUID] = None
    plant: Optional[PlantResponse] = None
    users: List["User"] = []



from app.users.models import User, UserRole
from app.audit.models import Audit
from app.audit_info.models import AuditInfo
from app.settings.links import UserDepartment
