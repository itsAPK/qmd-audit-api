from sqlmodel import Relationship, SQLModel, Field
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID



class UserDepartment(SQLModel, table=True):
    user_id: UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    )
    department_id: UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("department.id", ondelete="CASCADE"), primary_key=True)
    )
    role_id: UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("userrole.id", ondelete="CASCADE"), primary_key=True)
    )

    user: "User" = Relationship(back_populates="departments")
    department: "Department" = Relationship(back_populates="users")
    role: "UserRole" = Relationship(back_populates="departments")

UserDepartment.model_rebuild()

from app.users.models import User, UserRole
from app.settings.models import Department,Company, Plant
    
    
