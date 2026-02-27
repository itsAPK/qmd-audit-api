from datetime import date, datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy import Column
from sqlmodel import Field, ForeignKey, Relationship
from app.core.schemas import BaseModel
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class ChecklistStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    DRAFTED = "DRAFTED"


class InternalAuditorsChecklistItem(BaseModel, table=True):
    activity_description: str
    applicable_functions: str
    audit_findings: str
    checklist_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("internalauditorschecklist.id", ondelete="CASCADE"), nullable=False
        )
    )
    checklist: "InternalAuditorsChecklist" = Relationship(back_populates="items")


class InternalAuditorsChecklist(BaseModel, table=True):
    internal_audit_number_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("auditinfo.id", ondelete="CASCADE"), nullable=False
        )
    )
    internal_audit_number: 'AuditInfo' = Relationship(back_populates="internal_audit_checklists")
    division: str
    audit_area: str
    location: str
    status: ChecklistStatus 
    items : List["InternalAuditorsChecklistItem"] = Relationship(
        back_populates="checklist",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    created_by_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        )
    )
    created_by: "User" = Relationship(back_populates="internal_auditors_checklists")


class InternalAuditObservationChecklistItem(BaseModel, table=True):
    sl_no: str
    procedure_ref: str
    qms_check_point: str
    observation: str
    clause_no: str
    ncr_type: str
    checklist_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("internalauditobservationchecklist.id", ondelete="CASCADE"), nullable=False
        )
    )
    checklist: "InternalAuditObservationChecklist" = Relationship(
        back_populates="items"
    )


class InternalAuditObservationChecklist(BaseModel, table=True):
    internal_audit_number_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("auditinfo.id", ondelete="CASCADE"), nullable=False
        )
    )
    division: str
    audit_area: str
    location: str
    status: ChecklistStatus
    items : List["InternalAuditObservationChecklistItem"] = Relationship(
        back_populates="checklist",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    auditee_name: str
    created_by_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        )
    )
    created_by: "User" = Relationship(
        back_populates="internal_audit_observation_checklists"
    )
    internal_audit_number: 'AuditInfo' = Relationship(back_populates="internal_audit_observation_checklists")


class BRCPWarehouseChecklist(BaseModel, table=True):
    internal_audit_number: str
    warehouse_incharge: str
    status: ChecklistStatus
    created_by: "User" = Relationship(back_populates="brcp_warehouse_checklists")
    chargers: List["ChargerInfrastructure"] = Relationship(back_populates="checklist")
    instruments: List["MeasuringInstrument"] = Relationship(back_populates="checklist")
    batteries: List["BatteryRefreshStatus"] = Relationship(back_populates="checklist")
    additional_info: Optional["WarehouseAdditionalInfo"] = Relationship(
        back_populates="checklist"
    )
    created_by_id : UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
        )
    )


class ChargerInfrastructure(BaseModel, table=True) :
    type: str  # 2W / 4W / VRLA / Tubular
    charger_serial_no: Optional[str] = None
    make: Optional[str] = None
    year_of_mfg: Optional[int] = None
    rating: Optional[str] = None
    channels_working: Optional[int] = None
    channels_not_working: Optional[int] = None
    calibration_due_on: Optional[date] = None
    work_instruction_available: Optional[bool] = None
    checklist: Optional["BRCPWarehouseChecklist"] = Relationship(
        back_populates="chargers"
    )
    checklist_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("brcpwarehousechecklist.id", ondelete="CASCADE"), nullable=False
        )
    )


class MeasuringInstrument(BaseModel, table=True):
    instrument_name: str  # Multimeter / Clamp meter
    imte_no: Optional[str] = None
    make: Optional[str] = None
    serial_no: Optional[str] = None
    calibration_due_on: Optional[date]
    checklist_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("brcpwarehousechecklist.id", ondelete="CASCADE"), nullable=False
        )
    )
    checklist: Optional["BRCPWarehouseChecklist"] = Relationship(
        back_populates="instruments"
    )
    


class WarehouseAdditionalInfo(BaseModel, table=True):
    checklist_id: UUID = Field(foreign_key="brcpwarehousechecklist.id", unique=True)
    operating_by: Optional[str] = None  # AREML / 3rd Party
    total_manpower: Optional[int] = None
    refresh_charging_manpower: Optional[int] = None
    power_cut_hours_per_day: Optional[float] = None
    dg_available: Optional[bool] = None
    additional_information: Optional[str] = None
    checklist: Optional["BRCPWarehouseChecklist"] = Relationship(
        back_populates="additional_info"
    )
    checklist_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("brcpwarehousechecklist.id", ondelete="CASCADE"), nullable=False
        )
    )


class BatteryRefreshStatus(BaseModel, table=True):
    checklist_id: UUID = Field(foreign_key="brcpwarehousechecklist.id")
    type: str  # 2W / 4W
    model: Optional[str] = None  # AM / PZ / Elito
    total_due_qty: Optional[int] = None
    ageing_91_180: Optional[int] = None
    refresh_91_180_date: Optional[date] = None
    ageing_181_270: Optional[int] = None
    refresh_181_270_date: Optional[date] = None
    ageing_271_360: Optional[int] = None
    refresh_271_360_date: Optional[date] = None
    ageing_361_450: Optional[int] = None
    refresh_361_450_date: Optional[date] = None
    ageing_451_540: Optional[int] = None
    refresh_451_540_date: Optional[date] = None
    ageing_above_540: Optional[int] = None
    remarks: Optional[str] = None
    checklist: Optional["BRCPWarehouseChecklist"] = Relationship(
        back_populates="batteries"
    )
    checklist_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("brcpwarehousechecklist.id", ondelete="CASCADE"), nullable=False
        )
    )
    
    

class FranchiseAuditChecklist(BaseModel, table=True):
    division: Optional[str] = None
    audit_area: Optional[str] = None
    location: Optional[str] = None
    franchise_name: Optional[str] = None
    audit_date: Optional[datetime] = None
    suggestions: Optional[str] = None

    status: ChecklistStatus = Field(
        default=ChecklistStatus.DRAFTED
    )

    service_engineer_sign: Optional[str] = None

    created_by_id: UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    created_by: "User" = Relationship(
        back_populates="franchise_audit_checklists"
    )

    observations: List["FranchiseAuditObservation"] = Relationship(
        back_populates="checklist"
    )
    
class FranchiseAuditObservation(BaseModel, table=True):
        section: str  
        # Infrastructure / Battery Charging / Other Observations
        sl_no: int
        requirement: str
        observation: Optional[str]
        checklist: Optional["FranchiseAuditChecklist"] = Relationship(back_populates="observations")
        checklist_id: UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("franchiseauditchecklist.id", ondelete="CASCADE"), nullable=False
        )
    )



class InternalAuditorsChecklistItemRequest(PydanticBaseModel):
    activity_description: str
    applicable_functions: str
    audit_findings: str



class InternalAuditorsChecklistRequested(PydanticBaseModel):
    internal_audit_number: str
    division: str
    audit_area: str
    location: str
    status: ChecklistStatus
    items: list[InternalAuditorsChecklistItemRequest] = []
    
    
class InternalAuditorsChecklistUpdate(PydanticBaseModel):
    internal_audit_number: Optional[str] = None
    division: Optional[str] = None
    audit_area: Optional[str] = None
    location: Optional[str] = None
    status: Optional[ChecklistStatus] = None
    items: Optional[List[InternalAuditorsChecklistItemRequest]] = None
    
    
    
class InternalAuditorsChecklistResponse(PydanticBaseModel):
    id: UUID
    internal_audit_number: Any
    division: str
    audit_area: str
    location: str
    status: ChecklistStatus
    items: list["InternalAuditorsChecklistItemResponse"] = []
    created_by : Optional["User"] = None
    created_at: datetime
    
class  InternalAuditorsChecklistItemResponse(PydanticBaseModel):
    id: UUID
    activity_description: str
    applicable_functions: str
    audit_findings: str
    checklist_id: UUID
    
class InternalAuditorsChecklistItemUpdate(PydanticBaseModel):
    activity_description: Optional[str] = None
    applicable_functions: Optional[str] = None
    audit_findings: Optional[str] = None
    
    
class InternalAuditorsChecklistListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data : list["InternalAuditorsChecklistResponse"]
    
class InternalAuditObservationChecklistRequest(PydanticBaseModel):
    internal_audit_number: str
    division: str
    audit_area: str
    location: str
    status: ChecklistStatus
    items: list["InternalAuditObservationChecklistItemRequest"] = []
    auditee_name: str
    
class InternalAuditObservationChecklistItemRequest(PydanticBaseModel):
    sl_no: str
    procedure_ref: str
    qms_check_point: str
    observation: str
    clause_no: str
    ncr_type: str
    
class InternalAuditObservationChecklistUpdate(PydanticBaseModel):
    internal_audit_number: Optional[str] = None
    division: Optional[str] = None
    audit_area: Optional[str] = None
    location: Optional[str] = None
    status: Optional[ChecklistStatus] = None
    auditee_name: Optional[str] = None
    observations: Optional[List["InternalAuditObservationChecklistItemRequest"]] = None

class InternalAuditObservationChecklistItemUpdate(PydanticBaseModel):
    sl_no: Optional[str] = None
    procedure_ref: Optional[str] = None
    qms_check_point: Optional[str] = None
    observation: Optional[str] = None
    clause_no: Optional[str] = None
    ncr_type: Optional[str] = None
    
class InternalAuditObservationChecklistItemResponse(PydanticBaseModel):
    id: UUID
    sl_no: str
    procedure_ref: str
    qms_check_point: str
    observation: str
    clause_no: str
    ncr_type: str
    checklist_id: UUID
    
class InternalAuditObservationChecklistResponse(PydanticBaseModel):
    id: UUID
    internal_audit_number: Any
    division: str
    audit_area: str
    location: str
    status: ChecklistStatus
    auditee_name: Optional[str] = None
    items: list["InternalAuditObservationChecklistItemResponse"] = []
    created_by : Optional["User"] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
class InternalAuditObservationChecklistListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data : list["InternalAuditObservationChecklistResponse"]
    
    
class FranchiseAuditChecklistRequest(PydanticBaseModel):
    division: Optional[str]
    audit_area: Optional[str]
    location: Optional[str]
    franchise_name: Optional[str]
    audit_date: Optional[datetime]
    suggestions: Optional[str]
    status : Optional[ChecklistStatus] = Field(default=ChecklistStatus.DRAFTED)
    service_engineer_sign: Optional[str]
    observations: List["FranchiseAuditObservationRequest"] = []
    
    
class FranchiseAuditObservationRequest(PydanticBaseModel):
        section: str  
        # Infrastructure / Battery Charging / Other Observations
        sl_no: int
        requirement: str
        observation: Optional[str]
        
    
    
class FranchiseAuditChecklistUpdate(PydanticBaseModel):
    division: Optional[str] = None
    audit_area: Optional[str] = None
    location: Optional[str] = None
    franchise_name: Optional[str] = None
    audit_date: Optional[datetime] = None
    suggestions: Optional[str] = None
    service_engineer_sign: Optional[str] = None
    status : Optional[ChecklistStatus] = None
    observations: Optional[List["FranchiseAuditObservationUpdate"]] = None
    
    
class FranchiseAuditObservationUpdate(PydanticBaseModel):
        section: Optional[str] = None  
        # Infrastructure / Battery Charging / Other Observations
        sl_no: Optional[int] = None
        requirement: Optional[str] = None
        observation: Optional[str] = None

class FranchiseAuditChecklistResponse(PydanticBaseModel):
    id: UUID
    division: str
    audit_area: str
    location: str
    franchise_name: str
    audit_date: datetime
    suggestions: str
    status : ChecklistStatus 
    service_engineer_sign: str
    observations: list["FranchiseAuditObservationResponse"] = []
    created_by : Optional["User"] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class FranchiseAuditObservationResponse(PydanticBaseModel):
        id: UUID
        section: str  
        # Infrastructure / Battery Charging / Other Observations
        sl_no: int
        requirement: str
        observation: Optional[str]
        
class FranchiseAuditChecklistListResponse(PydanticBaseModel):
    total: int
    current_page: int
    page_size: int
    total_pages: int
    data : list["FranchiseAuditChecklistResponse"]

from app.users.models import User
from app.audit_info.models import AuditInfo