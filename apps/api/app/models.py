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
    Date,
    Time,
    JSON,
    ForeignKey,
    CheckConstraint,
    Index,
    UniqueConstraint,
    func,
    text,
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
    source = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, nullable=False, server_default="false", index=True)
    is_demo = Column(Boolean, nullable=False, server_default="false", index=True)
    operational_status = Column(String(30), nullable=False, server_default="unknown", index=True)
    emergency_services = Column(Boolean, nullable=True)
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
    specialities = relationship("Speciality", secondary="hospital_specialities", back_populates="hospitals")
    opds = relationship("OPD", back_populates="hospital")

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
        CheckConstraint("NOT is_verified OR (verified_at IS NOT NULL AND source IS NOT NULL AND length(trim(source)) > 0)", name="chk_hospitals_verified_provenance"),
        CheckConstraint("NOT (is_demo AND is_verified)", name="chk_hospitals_demo_unverified"),
        CheckConstraint("operational_status IN ('unknown', 'operational', 'not_operational')", name="chk_hospitals_operational_status"),
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
    schedule_json = Column(JSON, nullable=True)
    languages = Column(String(255), nullable=True)
    consultation_fee = Column(Numeric(10, 2), nullable=True)
    phone = Column(String(50), nullable=True)
    source = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, nullable=False, server_default="false", index=True)
    is_demo = Column(Boolean, nullable=False, server_default="false", index=True)
    operational_status = Column(String(30), nullable=False, server_default="unknown", index=True)
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
    specialities = relationship("Speciality", secondary="doctor_specialities", back_populates="doctors")

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
        CheckConstraint("NOT is_verified OR (verified_at IS NOT NULL AND source IS NOT NULL AND length(trim(source)) > 0)", name="chk_doctors_verified_provenance"),
        CheckConstraint("NOT (is_demo AND is_verified)", name="chk_doctors_demo_unverified"),
        CheckConstraint("operational_status IN ('unknown', 'operational', 'not_operational')", name="chk_doctors_operational_status"),
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
    source = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, nullable=False, server_default="false", index=True)
    is_demo = Column(Boolean, nullable=False, server_default="false", index=True)
    operational_status = Column(String(30), nullable=False, server_default="unknown", index=True)
    home_sample_collection = Column(Boolean, nullable=True)
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
        CheckConstraint("NOT is_verified OR (verified_at IS NOT NULL AND source IS NOT NULL AND length(trim(source)) > 0)", name="chk_diagnostic_labs_verified_provenance"),
        CheckConstraint("NOT (is_demo AND is_verified)", name="chk_diagnostic_labs_demo_unverified"),
        CheckConstraint("operational_status IN ('unknown', 'operational', 'not_operational')", name="chk_diagnostic_labs_operational_status"),
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


class Speciality(Base):
    __tablename__ = "specialities"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    slug = Column(String(140), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    hospitals = relationship("Hospital", secondary="hospital_specialities", back_populates="specialities")
    doctors = relationship("Doctor", secondary="doctor_specialities", back_populates="specialities")


class HospitalSpeciality(Base):
    __tablename__ = "hospital_specialities"
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True)
    speciality_id = Column(Integer, ForeignKey("specialities.id", ondelete="CASCADE"), primary_key=True)
    __table_args__ = (Index("ix_hospital_specialities_speciality_id", "speciality_id"),)


class DoctorSpeciality(Base):
    __tablename__ = "doctor_specialities"
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True)
    speciality_id = Column(Integer, ForeignKey("specialities.id", ondelete="CASCADE"), primary_key=True)
    __table_args__ = (Index("ix_doctor_specialities_speciality_id", "speciality_id"),)


class OPD(Base):
    __tablename__ = "opds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    opd_type = Column(String(100), nullable=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    address = Column(Text, nullable=True)
    locality = Column(String(255), nullable=True, index=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    pincode = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    operating_hours = Column(Text, nullable=True)
    source = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, nullable=False, server_default="false", index=True)
    is_demo = Column(Boolean, nullable=False, server_default="false", index=True)
    operational_status = Column(String(30), nullable=False, server_default="unknown", index=True)
    verification_status = Column(String(50), nullable=False, server_default="unverified", index=True)
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hospital = relationship("Hospital", back_populates="opds")

    __table_args__ = (
        CheckConstraint("verification_status IN ('unverified', 'pending', 'verified', 'rejected')", name="chk_opds_verification_status"),
        CheckConstraint("NOT is_verified OR (verified_at IS NOT NULL AND source IS NOT NULL AND length(trim(source)) > 0)", name="chk_opds_verified_provenance"),
        CheckConstraint("NOT (is_demo AND is_verified)", name="chk_opds_demo_unverified"),
        CheckConstraint("operational_status IN ('unknown', 'operational', 'not_operational')", name="chk_opds_operational_status"),
        Index("ix_opds_city_state", "city", "state"),
        Index("ix_opds_verification_active", "verification_status", "is_active"),
    )


class User(Base):
    """Application users supporting patient, provider, and admin roles.

    Provider account creation and provider ownership verification of listings
    are NOT part of this foundation and are intentionally not implemented here.

    A provider account MAY later be linked to a specific provider listing
    (hospital, doctor, lab, or OPD) via provider_listing_id / provider_listing_type.
    No provider account is assumed to own every listing by default.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        String(30), nullable=False, server_default="patient", index=True
    )
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    is_verified = Column(Boolean, nullable=False, server_default="false")
    # Optional link to a specific provider listing this provider account manages.
    # Nullable: a provider account is not assumed to own every listing.
    provider_listing_id = Column(Integer, nullable=True, index=True)
    provider_listing_type = Column(String(30), nullable=True)
    provider_doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    family_members = relationship("FamilyMember", back_populates="user", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    doctor_profile = relationship("Doctor", foreign_keys=[provider_doctor_id])

    __table_args__ = (
        CheckConstraint(
            "role IN ('patient', 'provider', 'admin')",
            name="chk_users_role",
        ),
    )


class Appointment(Base):
    """A patient-owned demo booking linked to a directory doctor."""

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(40), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    appointment_date = Column(Date, nullable=False, index=True)
    appointment_time = Column(Time, nullable=False)
    location = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False)
    package_id = Column(
        Integer, ForeignKey("packages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    legacy_package_id = Column(String(100), nullable=True)
    package_name = Column(String(255), nullable=True)
    package_amount = Column(Numeric(10, 2), nullable=False, server_default="0")
    consultation_fee = Column(Numeric(10, 2), nullable=False, server_default="0")
    service_charge = Column(Numeric(10, 2), nullable=False, server_default="0")
    total_amount = Column(Numeric(10, 2), nullable=False, server_default="0")
    advance_paid = Column(Numeric(10, 2), nullable=False, server_default="0")
    remaining_balance = Column(Numeric(10, 2), nullable=False, server_default="0")
    status = Column(String(30), nullable=False, server_default="demo_confirmed", index=True)
    payment_status = Column(String(30), nullable=False, server_default="demo_unpaid")
    is_demo = Column(Boolean, nullable=False, server_default="true", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="appointments")
    doctor = relationship("Doctor")
    package = relationship("Package")
    invoice = relationship("Invoice", back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    payments = relationship("PaymentRecord", back_populates="appointment", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('demo_confirmed', 'pending', 'completed', 'cancelled')", name="chk_appointments_status"),
        CheckConstraint("payment_status IN ('demo_unpaid', 'demo_recorded', 'paid', 'refunded')", name="chk_appointments_payment_status"),
        CheckConstraint("package_amount >= 0 AND consultation_fee >= 0 AND service_charge >= 0 AND total_amount >= 0 AND advance_paid >= 0 AND remaining_balance >= 0", name="chk_appointments_amounts_non_negative"),
        UniqueConstraint("reference", name="appointments_reference_key"),
        Index(
            "uq_appointment_doctor_slot_active",
            "doctor_id",
            "appointment_date",
            "appointment_time",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
            sqlite_where=text("status <> 'cancelled'"),
        ),
        Index("ix_appointments_doctor_schedule", "doctor_id", "appointment_date", "appointment_time"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(40), nullable=False, unique=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    package_amount = Column(Numeric(10, 2), nullable=False, server_default="0")
    consultation_fee = Column(Numeric(10, 2), nullable=False, server_default="0")
    service_charge = Column(Numeric(10, 2), nullable=False, server_default="0")
    total_amount = Column(Numeric(10, 2), nullable=False, server_default="0")
    advance_paid = Column(Numeric(10, 2), nullable=False, server_default="0")
    outstanding_balance = Column(Numeric(10, 2), nullable=False, server_default="0")
    is_demo = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    appointment = relationship("Appointment", back_populates="invoice")
    user = relationship("User", back_populates="invoices")
    payments = relationship("PaymentRecord", back_populates="invoice")

    __table_args__ = (
        UniqueConstraint("invoice_number", name="invoices_invoice_number_key"),
        UniqueConstraint("appointment_id", name="invoices_appointment_id_key"),
    )


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False, server_default="0")
    method_label = Column(String(50), nullable=False, server_default="demo")
    status = Column(String(30), nullable=False, server_default="demo_not_charged")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    appointment = relationship("Appointment", back_populates="payments")
    invoice = relationship("Invoice", back_populates="payments")
    __table_args__ = (UniqueConstraint("appointment_id", name="uq_payment_appointment"),)


class DoctorApplication(Base):
    __tablename__ = "doctor_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, server_default="pending", index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    applicant = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    doctor = relationship("Doctor")

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_doctor_applications_status"),
        UniqueConstraint("doctor_id", name="doctor_applications_doctor_id_key"),
    )
class PackageInclusion(Base):
    __tablename__ = "package_inclusions"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    test_name = Column(String(255), nullable=False)
    display_order = Column(Integer, nullable=False, server_default="0")

    package = relationship("Package", back_populates="inclusions")

class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    provider_name = Column(String(255), nullable=False)
    provider_type = Column(String(50), nullable=False, server_default="diagnostic_lab", index=True)
    price = Column(Numeric(10, 2), nullable=False, server_default="0")
    currency = Column(String(10), nullable=False, server_default="INR")
    city = Column(String(100), nullable=False, server_default="Raichur", index=True)
    state = Column(String(100), nullable=False, server_default="Karnataka", index=True)
    locality = Column(String(255), nullable=True, index=True)
    category = Column(String(50), nullable=False, server_default="checkup", index=True)
    source = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=True)
    min_age_years = Column(Integer, nullable=True)
    max_age_years = Column(Integer, nullable=True)
    validity_period = Column(String(20), nullable=True)
    validity_description = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, nullable=False, server_default="false", index=True)
    is_demo = Column(Boolean, nullable=False, server_default="false", index=True)
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


    inclusions = relationship(
        "PackageInclusion",
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="PackageInclusion.display_order",
    )
    subscriptions = relationship("Subscription", back_populates="plan")

    __table_args__ = (
        CheckConstraint("price >= 0", name="chk_packages_price_non_negative"),
        CheckConstraint(
            "provider_type IN ('hospital', 'diagnostic_lab')",
            name="chk_packages_provider_type",
        ),
        CheckConstraint(
            "category IN ('checkup', 'dental', 'vaccination', 'other')",
            name="chk_packages_category",
        ),
        CheckConstraint(
            "(min_age_years IS NULL OR min_age_years BETWEEN 0 AND 130) AND "
            "(max_age_years IS NULL OR max_age_years BETWEEN 0 AND 130) AND "
            "(min_age_years IS NULL OR max_age_years IS NULL OR min_age_years <= max_age_years)",
            name="chk_packages_age_range",
        ),
        CheckConstraint(
            "validity_period IS NULL OR validity_period IN ('monthly', 'quarterly', 'yearly')",
            name="chk_packages_validity_period",
        ),
        Index("ix_packages_city_state", "city", "state"),
        Index("ix_packages_category_active", "category", "is_active"),
    )


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    relationship_type = Column(String(30), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="family_members")
    reminders = relationship(
        "Reminder",
        back_populates="family_member",
        cascade="all, delete-orphan",
    )
    subscriptions = relationship("Subscription", back_populates="family_member")

    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('self', 'father', 'mother', 'child', 'other')",
            name="chk_family_members_relationship",
        ),
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    family_member_id = Column(Integer, ForeignKey("family_members.id", ondelete="CASCADE"), nullable=True, index=True)
    subscription_id = Column(
        Integer, ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    title = Column(String(255), nullable=False)
    category = Column(String(30), nullable=False)
    reminder_date = Column(Date, nullable=False, index=True)
    repeat_interval = Column(String(30), nullable=False, server_default="none")
    completed = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")
    family_member = relationship("FamilyMember", back_populates="reminders")
    subscription = relationship("Subscription", back_populates="reminder", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "category IN ('checkup', 'dental', 'vaccination', 'other')",
            name="chk_reminders_category",
        ),
        CheckConstraint(
            "repeat_interval IN ('none', 'daily', 'weekly', 'monthly', 'yearly', 'half-yearly')",
            name="chk_reminders_repeat",
        ),
        UniqueConstraint("subscription_id", name="uq_reminders_subscription_id"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("packages.id", ondelete="RESTRICT"), nullable=False, index=True)
    family_member_id = Column(
        Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True, index=True
    )
    age_years_at_start = Column(Integer, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, server_default="INR")
    start_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(30), nullable=False, server_default="pending_payment", index=True)
    payment_status = Column(String(30), nullable=False, server_default="pending", index=True)
    renewal_of_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Package", back_populates="subscriptions")
    family_member = relationship("FamilyMember", back_populates="subscriptions")
    renewed_from = relationship(
        "Subscription",
        remote_side=[id],
        foreign_keys=[renewal_of_id],
        back_populates="renewal",
    )
    renewal = relationship(
        "Subscription",
        foreign_keys=[renewal_of_id],
        back_populates="renewed_from",
        uselist=False,
    )
    reminder = relationship("Reminder", back_populates="subscription", uselist=False)
    events = relationship(
        "SubscriptionEvent",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="(SubscriptionEvent.created_at, SubscriptionEvent.id)",
    )

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_subscriptions_amount_non_negative"),
        CheckConstraint(
            "age_years_at_start IS NULL OR age_years_at_start BETWEEN 0 AND 130",
            name="chk_subscriptions_age_non_negative",
        ),
        CheckConstraint("expires_at > start_at", name="chk_subscriptions_valid_dates"),
        CheckConstraint(
            "status IN ('pending_payment', 'scheduled', 'active', 'expired', 'cancelled')",
            name="chk_subscriptions_status",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'simulated', 'paid', 'failed', 'refunded')",
            name="chk_subscriptions_payment_status",
        ),
        UniqueConstraint("renewal_of_id", name="uq_subscriptions_renewal_of_id"),
        Index("ix_subscriptions_user_status", "user_id", "status"),
        Index(
            "uq_subscription_user_plan_open",
            "user_id",
            "plan_id",
            unique=True,
            postgresql_where=text(
                "renewal_of_id IS NULL AND status IN ('pending_payment', 'scheduled', 'active')"
            ),
            sqlite_where=text(
                "renewal_of_id IS NULL AND status IN ('pending_payment', 'scheduled', 'active')"
            ),
        ),
    )

    @property
    def renewal_subscription_id(self):
        return self.renewal.id if self.renewal is not None else None


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(
        Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(40), nullable=False)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    payment_status = Column(String(30), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    subscription = relationship("Subscription", back_populates="events")
    actor = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created', 'activated', 'payment_simulated', 'payment_confirmed', "
            "'payment_failed', 'renewed', 'cancelled', 'expired')",
            name="chk_subscription_events_type",
        ),
        CheckConstraint(
            "new_status IN ('pending_payment', 'scheduled', 'active', 'expired', 'cancelled')",
            name="chk_subscription_events_status",
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'simulated', 'paid', 'failed', 'refunded')",
            name="chk_subscription_events_payment_status",
        ),
        CheckConstraint("amount >= 0", name="chk_subscription_events_amount_non_negative"),
        Index("ix_subscription_events_created_at", "subscription_id", "created_at"),
    )