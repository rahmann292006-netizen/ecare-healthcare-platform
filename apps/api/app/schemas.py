"""Pydantic request and response schemas for the eCare API.

All schemas are designed for the public healthcare discovery platform.
New listings always default to verification_status="unverified" and
clients cannot set verification_status to "verified" via the API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re


def slugify(value: str) -> str:
    """Convert a human-readable name into a URL-safe slug."""
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-") or "untitled"


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
    emergency_services: Optional[bool] = Field(False, description="Emergency services available")
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
    operating_hours: Optional[str] = None

    @model_validator(mode="after")
    def _regenerate_slug_if_name_changed(self):
        if self.name is not None and self.slug is None:
            self.slug = slugify(self.name)
        return self


class HospitalResponse(HospitalBase):
    """Response schema for a hospital."""

    id: int
    verification_status: str
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

    @model_validator(mode="after")
    def _regenerate_slug_if_name_changed(self):
        if self.full_name is not None and self.slug is None:
            self.slug = slugify(self.full_name)
        return self


class DoctorResponse(DoctorBase):
    id: int
    verification_status: str
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
    home_sample_collection: Optional[bool] = Field(False)

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

    @model_validator(mode="after")
    def _regenerate_slug_if_name_changed(self):
        if self.name is not None and self.slug is None:
            self.slug = slugify(self.name)
        return self


class LabResponse(LabBase):
    id: int
    verification_status: str
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