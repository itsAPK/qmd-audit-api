from datetime import datetime
from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4
from enum import Enum
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel
from typing import Generic, TypeVar
from pydantic.generics import GenericModel

T = TypeVar("T")

class BaseModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.now},
    )
    


class ResponseStatus(Enum):
    SUCCESS = "SUCCESS"
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    BAD_REQUEST = "BAD_REQUEST"
    ALREADY_EXIST = "ALREADY_EXIST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    FAILED = "FAILED"
    RETRIEVED = "RETRIEVED"
    ACCEPTED = "ACCEPTED"
    NOT_FOUND = "NOT_FOUND"
    


class Response(GenericModel, Generic[T]):
    message: str
    success: bool
    status: ResponseStatus
    data: Optional[T] = None
    
        
        
class FilterRequest(PydanticBaseModel):
    filter: list[dict] = []