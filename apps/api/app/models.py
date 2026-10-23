"""SQLAlchemy ORM models for the eCare healthcare directory.

Defines Hospitals, Doctors, Diagnostic Laboratories, and Diagnostic Tests
with appropriate constraints, indexes, and relationships.

Verification status values: unverified, pending, verified, rejected.
Default verification status: unverified.
Default city: Raichur; default state: Karnataka.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    hospital_type = Column(String(100), nullable=True)
    address = Column(Text, nullable=False)
    locality = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False, server_default="Raichur", index=True)
    state = Column(String(100), nullable=False, server_default="Karnataka", index=True)
    pincode = Column(String(20), nullable=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    emergency_services = Column(Boolean, nullable=False, server_default="false")
    operating_hours = Column(Text, nullable=True)
    verification_status = Column(
        String(50), nullable=False, server_default="unverified", index=True
    )
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    doctors = relationship("Doctor", back_populates="hospital", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="chk_hospitals_latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="chk_hospitals_longitude_range",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'pending', 'verified', 'rejected')",
            name="chk_hospitals_verification_status",
        ),
        Index("ix_hospitals_city_state", "city", "state"),
        Index("ix_hospitals_verification_active", "verification_status", "is_active"),
    )


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    qualifications = Column(Text, nullable=True)
    specializations = Column(String(255), nullable=True, index=True)
    experience_years = Column(Integer, nullable=True)
    languages = Column(String(255), nullable=True)
    consultation_fee = Column(Numeric(10, 2), nullable=True)
    phone = Column(String(50), nullable=True)
    hospital_id = Column(
        Integer, ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verification_status = Column(
        String(50), nullable=False, server_default="unverified", index=True
    )
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    hospital = relationship("Hospital", back_populates="doctors")

    __table_args__ = (
        CheckConstraint(
            "experience_years IS NULL OR experience_years >= 0",
            name="chk_doctors_experience_years_non_negative",
        ),
        CheckConstraint(
            "consultation_fee IS NULL OR consultation_fee >= 0",
            name="chk_doctors_consultation_fee_non_negative",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'pending', 'verified', 'rejected')",
            name="chk_doctors_verification_status",
        ),
        Index("ix_doctors_hospital_id", "hospital_id"),
        Index("ix_doctors_specialization", "specializations"),
        Index("ix_doctors_verification_active", "verification_status", "is_active"),
    )


class DiagnosticLab(Base):
    __tablename__ = "diagnostic_labs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    address = Column(Text, nullable=False)
    locality = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False, server_default="Raichur", index=True)
    state = Column(String(100), nullable=False, server_default="Karnataka", index=True)
    phone = Column(String(50), nullable=True)
    home_sample_collection = Column(Boolean, nullable=False, server_default="false")
    verification_status = Column(
        String(50), nullable=False, server_default="unverified", index=True
    )
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tests = relationship(
        "DiagnosticTest", back_populates="lab", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified', 'pending', 'verified', 'rejected')",
            name="chk_diagnostic_labs_verification_status",
        ),
        Index("ix_diagnostic_labs_city_state", "city", "state"),
        Index("ix_diagnostic_labs_verification_active", "verification_status", "is_active"),
    )


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"

    id = Column(Integer, primary_key=True, index=True)
    lab_id = Column(
        Integer,
        ForeignKey("diagnostic_labs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=True)
    preparation_instructions = Column(Text, nullable=True)
    availability_status = Column(String(100), nullable=False, server_default="available")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    lab = relationship("DiagnosticLab", back_populates="tests")

    __table_args__ = (
        CheckConstraint("price IS NULL OR price >= 0", name="chk_diagnostic_tests_price_non_negative"),
        CheckConstraint(
            "availability_status IN ('available', 'unavailable', 'temporarily_unavailable')",
            name="chk_diagnostic_tests_availability_status",
        ),
        Index("ix_diagnostic_tests_lab_id", "lab_id"),
        Index("ix_diagnostic_tests_availability", "availability_status"),
    )