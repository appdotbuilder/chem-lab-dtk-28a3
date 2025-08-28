from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy import DateTime, func
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
from decimal import Decimal


# Enums for various status fields
class UserRole(str, Enum):
    admin = "admin"
    kepala_lab = "kepala_lab"
    laboran = "laboran"
    dosen = "dosen"
    mahasiswa = "mahasiswa"


class EquipmentStatus(str, Enum):
    available = "available"
    in_use = "in_use"
    maintenance = "maintenance"
    decommissioned = "decommissioned"


class LoanStatus(str, Enum):
    pending = "pending"
    needs_head_approval = "needs_head_approval"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    in_use = "in_use"
    returned = "returned"
    late = "late"


class MaintenanceType(str, Enum):
    maintenance = "maintenance"
    calibration = "calibration"
    repair = "repair"


class NotificationType(str, Enum):
    pending_registration = "pending_registration"
    verification = "verification"
    new_request = "new_request"
    approve_reject = "approve_reject"
    due_today = "due_today"
    overdue = "overdue"
    password_reset = "password_reset"


# Persistent models (stored in database)
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    name: str = Field(max_length=100)
    email: str = Field(unique=True, max_length=255, index=True)
    role: UserRole = Field(index=True)
    password_hash: str = Field(max_length=255)
    is_active: bool = Field(default=True, index=True)
    is_verified: bool = Field(default=False, index=True)
    npm: Optional[str] = Field(default=None, max_length=20, index=True)  # For mahasiswa
    nip: Optional[str] = Field(default=None, max_length=30, index=True)  # For staff
    phone: Optional[str] = Field(default=None, max_length=20)
    lab_id: Optional[str] = Field(default=None, foreign_key="labs.id")
    must_change_password: bool = Field(default=False)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Relationships
    lab: Optional["Lab"] = Relationship(back_populates="laborans")
    loans_as_borrower: List["Loan"] = Relationship(
        back_populates="borrower", sa_relationship_kwargs={"foreign_keys": "[Loan.borrower_id]"}
    )
    loans_as_supervisor: List["Loan"] = Relationship(
        back_populates="supervisor", sa_relationship_kwargs={"foreign_keys": "[Loan.supervisor_id]"}
    )
    notifications: List["Notification"] = Relationship(back_populates="user")
    audit_logs: List["AuditLog"] = Relationship(back_populates="user")
    training_certificates: List["TrainingCertificate"] = Relationship(back_populates="user")


class Lab(SQLModel, table=True):
    __tablename__ = "labs"  # type: ignore[assignment]

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    code: str = Field(unique=True, max_length=10, index=True)
    name: str = Field(max_length=100)
    location: str = Field(max_length=200)
    capacity: int = Field(ge=1)
    operating_hours: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    head_id: Optional[str] = Field(default=None, foreign_key="users.id")
    contact_person: str = Field(max_length=100)
    contact_email: str = Field(max_length=255)
    rules_pdf: Optional[str] = Field(default=None, max_length=500)  # File path
    sop_pdf: Optional[str] = Field(default=None, max_length=500)  # File path
    gallery: List[str] = Field(default=[], sa_column=Column(JSON))  # Image paths
    description: str = Field(default="", max_length=2000)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Relationships
    head: Optional["User"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Lab.head_id]", "post_update": True})
    laborans: List["User"] = Relationship(back_populates="lab")
    equipment: List["Equipment"] = Relationship(back_populates="lab")
    loans: List["Loan"] = Relationship(back_populates="lab")


class Equipment(SQLModel, table=True):
    __tablename__ = "equipment"  # type: ignore[assignment]

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    lab_id: str = Field(foreign_key="labs.id", index=True)
    code: str = Field(max_length=50, index=True)  # Unique per lab
    name: str = Field(max_length=200)
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    serial_no: Optional[str] = Field(default=None, max_length=100)
    image: Optional[str] = Field(default=None, max_length=500)  # Image path
    specification: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    manual_pdf: Optional[str] = Field(default=None, max_length=500)  # File path
    status: EquipmentStatus = Field(default=EquipmentStatus.available, index=True)
    needs_head_approval: bool = Field(default=False)
    calibration_due_date: Optional[date] = Field(default=None)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Relationships
    lab: "Lab" = Relationship(back_populates="equipment")
    loans: List["Loan"] = Relationship(back_populates="equipment")
    maintenance_records: List["Maintenance"] = Relationship(back_populates="equipment")
    training_certificates: List["TrainingCertificate"] = Relationship(back_populates="equipment")


class Loan(SQLModel, table=True):
    __tablename__ = "loans"  # type: ignore[assignment]

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    equipment_id: str = Field(foreign_key="equipment.id", index=True)
    borrower_id: str = Field(foreign_key="users.id", index=True)
    supervisor_id: Optional[str] = Field(default=None, foreign_key="users.id")
    lab_id: str = Field(foreign_key="labs.id", index=True)  # Denormalized
    start_time: datetime = Field(index=True)
    end_time: datetime = Field(index=True)
    purpose: str = Field(max_length=500)
    course: Optional[str] = Field(default=None, max_length=100)
    project: Optional[str] = Field(default=None, max_length=200)
    jsa_pdf: str = Field(max_length=500)  # Mandatory JSA file path
    status: LoanStatus = Field(default=LoanStatus.pending, index=True)
    approved_by: Optional[str] = Field(default=None, foreign_key="users.id")
    head_approved_by: Optional[str] = Field(default=None, foreign_key="users.id")
    checkout_by: Optional[str] = Field(default=None, foreign_key="users.id")
    checkin_by: Optional[str] = Field(default=None, foreign_key="users.id")
    checkout_condition: Optional[str] = Field(default=None, max_length=1000)
    checkin_condition: Optional[str] = Field(default=None, max_length=1000)
    photo_before: Optional[str] = Field(default=None, max_length=500)
    photo_after: Optional[str] = Field(default=None, max_length=500)
    late_minutes: int = Field(default=0)
    damage_report: Optional[str] = Field(default=None, max_length=2000)
    damage_cost: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=12)
    notes: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

    # Relationships
    equipment: "Equipment" = Relationship(back_populates="loans")
    borrower: "User" = Relationship(
        back_populates="loans_as_borrower", sa_relationship_kwargs={"foreign_keys": "[Loan.borrower_id]"}
    )
    supervisor: Optional["User"] = Relationship(
        back_populates="loans_as_supervisor", sa_relationship_kwargs={"foreign_keys": "[Loan.supervisor_id]"}
    )
    lab: "Lab" = Relationship(back_populates="loans")


class Maintenance(SQLModel, table=True):
    __tablename__ = "maintenance"  # type: ignore[assignment]

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    equipment_id: str = Field(foreign_key="equipment.id", index=True)
    type: MaintenanceType = Field(index=True)
    date: datetime = Field(index=True)
    notes: str = Field(max_length=2000)
    doc_pdf: Optional[str] = Field(default=None, max_length=500)
    cost: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=12)
    performed_by: Optional[str] = Field(default=None, max_length=200)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    # Relationships
    equipment: "Equipment" = Relationship(back_populates="maintenance_records")


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"  # type: ignore[assignment]

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    user_id: str = Field(foreign_key="users.id", index=True)
    type: NotificationType = Field(index=True)
    title: str = Field(max_length=200)
    message: str = Field(max_length=1000)
    payload: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    is_read: bool = Field(default=False, index=True)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True))

    # Relationships
    user: "User" = Relationship(back_populates="notifications")


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"  # type: ignore[assignment]

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    user_id: Optional[str] = Field(default=None, foreign_key="users.id", index=True)
    action: str = Field(max_length=100, index=True)
    entity: str = Field(max_length=100, index=True)
    entity_id: Optional[str] = Field(default=None, max_length=36, index=True)
    detail: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True))

    # Relationships
    user: Optional["User"] = Relationship(back_populates="audit_logs")


class Setting(SQLModel, table=True):
    __tablename__ = "settings"  # type: ignore[assignment]

    key: str = Field(primary_key=True, max_length=100)
    value: Dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))


class TrainingCertificate(SQLModel, table=True):
    __tablename__ = "training_certificates"  # type: ignore[assignment]

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36)
    user_id: str = Field(foreign_key="users.id", index=True)
    equipment_id: str = Field(foreign_key="equipment.id", index=True)
    issued_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    expires_at: Optional[datetime] = Field(default=None)
    certificate_pdf: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    # Relationships
    user: "User" = Relationship(back_populates="training_certificates")
    equipment: "Equipment" = Relationship(back_populates="training_certificates")


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    email: str = Field(max_length=255)
    role: UserRole
    npm: Optional[str] = Field(default=None, max_length=20)
    nip: Optional[str] = Field(default=None, max_length=30)
    phone: Optional[str] = Field(default=None, max_length=20)
    lab_id: Optional[str] = Field(default=None, max_length=36)


class UserUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    lab_id: Optional[str] = Field(default=None, max_length=36)
    is_active: Optional[bool] = Field(default=None)


class StudentRegister(SQLModel, table=False):
    name: str = Field(max_length=100)
    email: str = Field(max_length=255)
    npm: str = Field(max_length=20)
    phone: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class PasswordReset(SQLModel, table=False):
    user_id: str = Field(max_length=36)
    new_password: str = Field(min_length=8, max_length=128)


class LabCreate(SQLModel, table=False):
    code: str = Field(max_length=10)
    name: str = Field(max_length=100)
    location: str = Field(max_length=200)
    capacity: int = Field(ge=1)
    operating_hours: Dict[str, Any] = Field(default={})
    head_id: Optional[str] = Field(default=None, max_length=36)
    contact_person: str = Field(max_length=100)
    contact_email: str = Field(max_length=255)
    description: str = Field(default="", max_length=2000)


class LabUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)
    capacity: Optional[int] = Field(default=None, ge=1)
    operating_hours: Optional[Dict[str, Any]] = Field(default=None)
    head_id: Optional[str] = Field(default=None, max_length=36)
    contact_person: Optional[str] = Field(default=None, max_length=100)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)


class EquipmentCreate(SQLModel, table=False):
    lab_id: str = Field(max_length=36)
    code: str = Field(max_length=50)
    name: str = Field(max_length=200)
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    serial_no: Optional[str] = Field(default=None, max_length=100)
    specification: Dict[str, Any] = Field(default={})
    needs_head_approval: bool = Field(default=False)
    calibration_due_date: Optional[date] = Field(default=None)


class EquipmentUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=200)
    brand: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    serial_no: Optional[str] = Field(default=None, max_length=100)
    specification: Optional[Dict[str, Any]] = Field(default=None)
    status: Optional[EquipmentStatus] = Field(default=None)
    needs_head_approval: Optional[bool] = Field(default=None)
    calibration_due_date: Optional[date] = Field(default=None)


class LoanCreate(SQLModel, table=False):
    equipment_id: str = Field(max_length=36)
    supervisor_id: Optional[str] = Field(default=None, max_length=36)
    start_time: datetime
    end_time: datetime
    purpose: str = Field(max_length=500)
    course: Optional[str] = Field(default=None, max_length=100)
    project: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=1000)


class LoanUpdate(SQLModel, table=False):
    status: Optional[LoanStatus] = Field(default=None)
    checkout_condition: Optional[str] = Field(default=None, max_length=1000)
    checkin_condition: Optional[str] = Field(default=None, max_length=1000)
    damage_report: Optional[str] = Field(default=None, max_length=2000)
    damage_cost: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=12)


class MaintenanceCreate(SQLModel, table=False):
    equipment_id: str = Field(max_length=36)
    type: MaintenanceType
    date: datetime
    notes: str = Field(max_length=2000)
    cost: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=12)
    performed_by: Optional[str] = Field(default=None, max_length=200)


class NotificationCreate(SQLModel, table=False):
    user_id: str = Field(max_length=36)
    type: NotificationType
    title: str = Field(max_length=200)
    message: str = Field(max_length=1000)
    payload: Dict[str, Any] = Field(default={})


class AuditLogCreate(SQLModel, table=False):
    user_id: Optional[str] = Field(default=None, max_length=36)
    action: str = Field(max_length=100)
    entity: str = Field(max_length=100)
    entity_id: Optional[str] = Field(default=None, max_length=36)
    detail: Dict[str, Any] = Field(default={})
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)


class SettingUpdate(SQLModel, table=False):
    value: Dict[str, Any]


class TrainingCertificateCreate(SQLModel, table=False):
    user_id: str = Field(max_length=36)
    equipment_id: str = Field(max_length=36)
    expires_at: Optional[datetime] = Field(default=None)


# Response schemas for API endpoints
class UserResponse(SQLModel, table=False):
    id: str
    name: str
    email: str
    role: UserRole
    is_active: bool
    is_verified: bool
    npm: Optional[str]
    nip: Optional[str]
    phone: Optional[str]
    lab_id: Optional[str]
    created_at: str  # ISO format
    updated_at: str  # ISO format


class LabResponse(SQLModel, table=False):
    id: str
    code: str
    name: str
    location: str
    capacity: int
    operating_hours: Dict[str, Any]
    head_id: Optional[str]
    contact_person: str
    contact_email: str
    description: str
    created_at: str  # ISO format


class EquipmentResponse(SQLModel, table=False):
    id: str
    lab_id: str
    code: str
    name: str
    brand: Optional[str]
    model: Optional[str]
    serial_no: Optional[str]
    specification: Dict[str, Any]
    status: EquipmentStatus
    needs_head_approval: bool
    calibration_due_date: Optional[str]  # ISO date format
    created_at: str  # ISO format


class LoanResponse(SQLModel, table=False):
    id: str
    equipment_id: str
    borrower_id: str
    supervisor_id: Optional[str]
    lab_id: str
    start_time: str  # ISO format
    end_time: str  # ISO format
    purpose: str
    course: Optional[str]
    project: Optional[str]
    status: LoanStatus
    late_minutes: int
    created_at: str  # ISO format
