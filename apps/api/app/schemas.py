"""Pydantic request and response schemas for the eCare API.

All schemas are designed for the public healthcare discovery platform.
New listings always default to verification_status="unverified" and
clients cannot set verification_status to "verified" via the API.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re

OperationalStatus = Literal["unknown", "operational", "not_operational"]


def slugify(value: str) -> str:
    """Convert a human-readable name into a URL-safe slug."""
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-") or "untitled"


class SpecialityResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Hospital schemas
# ---------------------------------------------------------------------------

class HospitalBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Hospital name")
    slug: Optional[str] = Field(None, max_length=255, description="URL-safe slug (auto-generated if omitted)")
    description: Optional[str] = Field(None, description="Hospital description")
    hospital_type: Optional[str] = Field(None, max_length=100, description="Type of hospital")
    address: str = Field(..., min_length=1, description="Street address")
    locality: Optional[str] = Field(None, max_length=255, description="Locality / area")
    city: Optional[str] = Field("Raichur", max_length=100, description="City")
    state: Optional[str] = Field("Karnataka", max_length=100, description="State")
    pincode: Optional[str] = Field(None, max_length=20, description="PIN code")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    website: Optional[str] = Field(None, max_length=500, description="Website URL")
    operational_status: OperationalStatus = Field("unknown", description="Provider operational status")
    emergency_services: Optional[bool] = Field(None, description="True/false when known; null when unknown")
    operating_hours: Optional[str] = Field(None, description="Operating hours text")

    @field_validator("slug", mode="before")
    @classmethod
    def _default_slug(cls, v):
        if v is None or v == "":
            return None
        return v

    @field_validator("city")
    @classmethod
    def _default_city(cls, v):
        return v or "Raichur"

    @field_validator("state")
    @classmethod
    def _default_state(cls, v):
        return v or "Karnataka"


class HospitalCreate(HospitalBase):
    """Request schema for creating a hospital.

    verification_status is intentionally excluded — it always defaults to
    "unverified" on the server side.
    """

    @model_validator(mode="after")
    def _generate_slug(self):
        if not self.slug:
            self.slug = slugify(self.name)
        return self


class HospitalUpdate(BaseModel):
    """Request schema for updating a hospital. All fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    hospital_type: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, min_length=1)
    locality: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    emergency_services: Optional[bool] = None
    operational_status: Optional[OperationalStatus] = None
    operating_hours: Optional[str] = None

    @model_validator(mode="after")
    def _regenerate_slug_if_name_changed(self):
        if self.name is not None and self.slug is None:
            self.slug = slugify(self.name)
        return self

    @model_validator(mode="after")
    def _reject_null_operational_status(self):
        if "operational_status" in self.model_fields_set and self.operational_status is None:
            raise ValueError("operational_status cannot be null")
        return self


class HospitalResponse(HospitalBase):
    """Response schema for a hospital."""

    id: int
    verification_status: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_verified: bool = False
    is_demo: bool = False
    specialities: list[SpecialityResponse] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HospitalListResponse(BaseModel):
    """Paginated list of hospitals."""

    items: list[HospitalResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Doctor schemas
# ---------------------------------------------------------------------------

class DoctorBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    qualifications: Optional[str] = None
    specializations: Optional[str] = Field(None, max_length=255)
    experience_years: Optional[int] = Field(None, ge=0)
    languages: Optional[str] = Field(None, max_length=255)
    consultation_fee: Optional[float] = Field(None, ge=0, description="Consultation fee in INR")
    phone: Optional[str] = Field(None, max_length=50)
    hospital_id: Optional[int] = Field(None, description="Associated hospital ID")
    operational_status: OperationalStatus = Field("unknown", description="Provider operational status")

    @field_validator("slug", mode="before")
    @classmethod
    def _default_slug(cls, v):
        if v is None or v == "":
            return None
        return v


class DoctorCreate(DoctorBase):
    """Request schema for creating a doctor.

    verification_status always defaults to "unverified" server-side.
    """

    @model_validator(mode="after")
    def _generate_slug(self):
        if not self.slug:
            self.slug = slugify(self.full_name)
        return self


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    qualifications: Optional[str] = None
    specializations: Optional[str] = Field(None, max_length=255)
    experience_years: Optional[int] = Field(None, ge=0)
    languages: Optional[str] = Field(None, max_length=255)
    consultation_fee: Optional[float] = Field(None, ge=0)
    phone: Optional[str] = Field(None, max_length=50)
    hospital_id: Optional[int] = None
    operational_status: Optional[OperationalStatus] = None

    @model_validator(mode="after")
    def _regenerate_slug_if_name_changed(self):
        if self.full_name is not None and self.slug is None:
            self.slug = slugify(self.full_name)
        return self

    @model_validator(mode="after")
    def _reject_null_operational_status(self):
        if "operational_status" in self.model_fields_set and self.operational_status is None:
            raise ValueError("operational_status cannot be null")
        return self


class DoctorResponse(DoctorBase):
    id: int
    verification_status: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_verified: bool = False
    is_demo: bool = False
    specialities: list[SpecialityResponse] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DoctorListResponse(BaseModel):
    items: list[DoctorResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Diagnostic Lab schemas
# ---------------------------------------------------------------------------

class LabBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    address: str = Field(..., min_length=1)
    locality: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field("Raichur", max_length=100)
    state: Optional[str] = Field("Karnataka", max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    operational_status: OperationalStatus = Field("unknown", description="Provider operational status")
    home_sample_collection: Optional[bool] = Field(None, description="True/false when known; null when unknown")

    @field_validator("slug", mode="before")
    @classmethod
    def _default_slug(cls, v):
        if v is None or v == "":
            return None
        return v


class LabCreate(LabBase):
    """Request schema for creating a diagnostic lab.

    verification_status always defaults to "unverified" server-side.
    """

    @model_validator(mode="after")
    def _generate_slug(self):
        if not self.slug:
            self.slug = slugify(self.name)
        return self


class LabUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    address: Optional[str] = Field(None, min_length=1)
    locality: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    home_sample_collection: Optional[bool] = None
    operational_status: Optional[OperationalStatus] = None

    @model_validator(mode="after")
    def _regenerate_slug_if_name_changed(self):
        if self.name is not None and self.slug is None:
            self.slug = slugify(self.name)
        return self

    @model_validator(mode="after")
    def _reject_null_operational_status(self):
        if "operational_status" in self.model_fields_set and self.operational_status is None:
            raise ValueError("operational_status cannot be null")
        return self


class LabResponse(LabBase):
    id: int
    verification_status: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_verified: bool = False
    is_demo: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LabListResponse(BaseModel):
    items: list[LabResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Diagnostic Test schemas
# ---------------------------------------------------------------------------

class TestBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0, description="Price in INR")
    preparation_instructions: Optional[str] = None
    availability_status: Optional[str] = Field("available", max_length=100)


class TestCreate(TestBase):
    """Request schema for creating a diagnostic test."""


class TestUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    preparation_instructions: Optional[str] = None
    availability_status: Optional[str] = Field(None, max_length=100)


class TestResponse(TestBase):
    id: int
    lab_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestListResponse(BaseModel):
    items: list[TestResponse]
    total: int
    limit: int
    offset: int


class ProviderDirectoryItem(BaseModel):
    id: int
    provider_type: str
    name: str
    slug: str
    description: Optional[str] = None
    address: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    hospital_type: Optional[str] = None
    opd_type: Optional[str] = None
    operating_hours: Optional[str] = None
    hospital_id: Optional[int] = None
    hospital_name: Optional[str] = None
    qualifications: Optional[str] = None
    experience_years: Optional[int] = None
    consultation_fee: Optional[float] = None
    schedule: Optional[dict] = None
    specialities: list[SpecialityResponse] = Field(default_factory=list)
    source: Optional[str] = None
    source_url: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_verified: bool = False
    is_demo: bool = False
    verification_status: str = "unverified"
    operational_status: OperationalStatus = "unknown"
    emergency_services: Optional[bool] = None
    home_sample_collection: Optional[bool] = None


class ProviderDirectoryResponse(BaseModel):
    items: list[ProviderDirectoryItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Authentication schemas
# ---------------------------------------------------------------------------

UserRole = Literal["patient", "provider", "admin"]


class UserBase(BaseModel):
    email: str = Field(..., max_length=255, description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    role: UserRole = Field("patient", description="User role")
    phone: Optional[str] = Field(None, max_length=50)


class UserCreate(BaseModel):
    """Request schema for public user registration.

    The role field is intentionally excluded: public registration always
    creates a patient account. Clients cannot set provider or admin roles.
    """

    email: str = Field(..., max_length=255, description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    phone: Optional[str] = Field(None, max_length=50)
    password: str = Field(..., min_length=8, max_length=128, description="Password")


class UserProvisionCreate(BaseModel):
    """Request schema for admin-only provisioning of user accounts.

    Only trusted administrators may create provider or admin accounts.
    Public registration cannot use this schema.
    """

    email: str = Field(..., max_length=255, description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    role: UserRole = Field("patient", description="User role (patient/provider/admin)")


class UserRead(UserBase):
    """Response schema for a user. Never includes the hashed password."""

    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class DoctorApplicationCreate(BaseModel):
    doctor_id: int = Field(..., ge=1, description="Existing doctor directory listing to link after approval")


class DoctorApplicationRead(BaseModel):
    id: int
    user_id: int
    doctor_id: int
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    applicant_name: Optional[str] = None
    applicant_email: Optional[str] = None
    doctor_name: Optional[str] = None


class UserLogin(BaseModel):
    """Request schema for user login."""

    email: str = Field(..., max_length=255, description="User email address")
    password: str = Field(..., description="Password")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(..., ge=1)
    appointment_date: date
    appointment_time: time
    location_id: Optional[str] = Field(None, max_length=100)
    package_id: Optional[int] = Field(None, ge=1, le=2_147_483_647)
    package_name: Optional[str] = Field(None, max_length=255)
    package_amount: Decimal = Field(Decimal("0"), ge=0, le=1000000)
    payment_method: Literal["demo"] = "demo"


class AppointmentStatusUpdate(BaseModel):
    status: Literal["demo_confirmed", "cancelled"]


class PaymentRead(BaseModel):
    id: int
    amount: Decimal
    method_label: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceRead(BaseModel):
    invoice_number: str
    appointment_id: int
    package_amount: Decimal
    consultation_fee: Decimal
    service_charge: Decimal
    total_amount: Decimal
    advance_paid: Decimal
    outstanding_balance: Decimal
    is_demo: bool
    created_at: datetime
    payments: list[PaymentRead] = Field(default_factory=list)
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    location: Optional[str] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None


class AppointmentRead(BaseModel):
    id: int
    reference: str
    user_id: int
    patient_name: Optional[str] = None
    doctor_id: int
    doctor_name: str
    doctor_qualification: Optional[str] = None
    doctor_speciality: Optional[str] = None
    hospital_id: Optional[int] = None
    hospital_name: Optional[str] = None
    appointment_date: date
    appointment_time: time
    location: str
    city: str
    state: str
    package_id: Optional[int] = None
    package_name: Optional[str] = None
    package_amount: Decimal
    consultation_fee: Decimal
    service_charge: Decimal
    total_amount: Decimal
    advance_paid: Decimal
    remaining_balance: Decimal
    status: str
    payment_status: str
    is_demo: bool
    created_at: datetime


class AppointmentDetail(AppointmentRead):
    invoice: InvoiceRead


class AppointmentAvailabilitySlot(BaseModel):
    time: time
    status: Literal["available", "unavailable"]
    reason: Optional[str] = None


class DoctorAppointmentAvailability(BaseModel):
    doctor_id: int
    appointment_date: date
    consultation_days: list[str] = Field(default_factory=list)
    opd_start: Optional[time] = None
    opd_end: Optional[time] = None
    clinic_location: Optional[str] = None
    consultation_fee: Optional[Decimal] = None
    duration_minutes: Optional[int] = None
    slots: list[AppointmentAvailabilitySlot] = Field(default_factory=list)
    fully_booked: bool = False
    message: Optional[str] = None


class DoctorScheduleUpdate(BaseModel):
    schedule: dict


# ---------------------------------------------------------------------------
# Family Members schemas
# ---------------------------------------------------------------------------

class FamilyMemberCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    relationship_type: Literal["self", "father", "mother", "child", "other"]


class FamilyMemberRead(BaseModel):
    id: int
    user_id: int
    name: str
    relationship_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Family Health Reminders schemas
# ---------------------------------------------------------------------------

class ReminderCreate(BaseModel):
    family_member_id: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=255)
    category: Literal["checkup", "dental", "vaccination", "other"]
    reminder_date: date
    repeat_interval: Literal[
        "none", "daily", "weekly", "monthly", "yearly", "half-yearly"
    ] = "none"


class ReminderUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[Literal["checkup", "dental", "vaccination", "other"]] = None
    reminder_date: Optional[date] = None
    repeat_interval: Optional[
        Literal["none", "daily", "weekly", "monthly", "yearly", "half-yearly"]
    ] = None
    completed: Optional[bool] = None


class ReminderRead(BaseModel):
    id: int
    user_id: int
    family_member_id: Optional[int]
    subscription_id: Optional[int] = None
    title: str
    category: str
    reminder_date: date
    repeat_interval: str
    completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Health checkup package schemas
# ---------------------------------------------------------------------------

class PackageInclusionBase(BaseModel):
    test_name: str = Field(..., min_length=1, max_length=255)
    display_order: int = Field(0, ge=0)


class PackageInclusionCreate(PackageInclusionBase):
    pass


class PackageInclusionRead(PackageInclusionBase):
    id: int
    package_id: int

    model_config = {"from_attributes": True}


class PackageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    provider_name: str = Field(..., min_length=1, max_length=255)
    provider_type: str = Field("diagnostic_lab", max_length=50, description="hospital or diagnostic_lab")
    price: float = Field(..., ge=0, description="Price in INR")
    currency: str = Field("INR", max_length=10)
    city: str = Field("Raichur", max_length=100)
    state: str = Field("Karnataka", max_length=100)
    locality: Optional[str] = Field(None, max_length=255)
    category: str = Field("checkup", max_length=50, description="checkup, dental, vaccination, or other")
    source: Optional[str] = None
    source_url: Optional[str] = None
    min_age_years: Optional[int] = Field(None, ge=0, le=130)
    max_age_years: Optional[int] = Field(None, ge=0, le=130)
    validity_period: Optional[Literal["monthly", "quarterly", "yearly"]] = None
    validity_description: Optional[str] = None

    @model_validator(mode="after")
    def _validate_age_range(self):
        if (
            self.min_age_years is not None
            and self.max_age_years is not None
            and self.min_age_years > self.max_age_years
        ):
            raise ValueError("min_age_years cannot exceed max_age_years")
        return self


class PackageCreate(PackageBase):
    inclusions: list[PackageInclusionCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _generate_slug(self):
        if not self.slug:
            self.slug = slugify(self.name)
        return self


class PackageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    provider_name: Optional[str] = Field(None, min_length=1, max_length=255)
    provider_type: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    locality: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=50)
    source: Optional[str] = None
    source_url: Optional[str] = None
    min_age_years: Optional[int] = Field(None, ge=0, le=130)
    max_age_years: Optional[int] = Field(None, ge=0, le=130)
    validity_period: Optional[Literal["monthly", "quarterly", "yearly"]] = None
    validity_description: Optional[str] = None
    inclusions: Optional[list[PackageInclusionCreate]] = None
    is_active: Optional[bool] = None


class PackageRead(PackageBase):
    id: int
    is_verified: bool
    is_demo: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    inclusions: list[PackageInclusionRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PackageListResponse(BaseModel):
    items: list[PackageRead]
    total: int
    limit: int
    offset: int


class PackageVerificationUpdate(BaseModel):
    source: str = Field(..., min_length=1, max_length=500)
    source_url: Optional[str] = Field(None, max_length=1000)


class SubscriptionCreate(BaseModel):
    plan_id: int = Field(..., ge=1, le=2_147_483_647)
    family_member_id: Optional[int] = Field(None, ge=1, le=2_147_483_647)
    age_years: Optional[int] = Field(None, ge=0, le=130)


class SubscriptionCancellationRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class SubscriptionEventRead(BaseModel):
    id: int
    actor_user_id: Optional[int]
    event_type: str
    previous_status: Optional[str]
    new_status: str
    payment_status: str
    amount: Decimal
    details: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionRead(BaseModel):
    id: int
    user_id: int
    plan_id: int
    family_member_id: Optional[int]
    age_years_at_start: Optional[int]
    amount: Decimal
    currency: str
    start_at: datetime
    expires_at: datetime
    status: Literal["pending_payment", "scheduled", "active", "expired", "cancelled"]
    payment_status: Literal["pending", "simulated", "paid", "failed", "refunded"]
    renewal_of_id: Optional[int]
    renewal_subscription_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    plan: PackageRead
    reminder: Optional[ReminderRead] = None
    events: list[SubscriptionEventRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SubscriptionPaymentOptionsRead(BaseModel):
    mode: Literal["simulated", "unavailable"]
    message: str
