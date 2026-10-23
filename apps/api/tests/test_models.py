"""Tests for SQLAlchemy model definitions, constraints, and relationships.

No real provider data is inserted. No credentials are logged or printed.
"""

import pytest
from sqlalchemy import CheckConstraint, inspect

from app.database import Base
from app.models import (
    Hospital, Doctor, DiagnosticLab, DiagnosticTest, Speciality,
    HospitalSpeciality, DoctorSpeciality, OPD,
)


def test_base_metadata_registers_all_models():
    """All four models are registered with SQLAlchemy Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "hospitals", "doctors", "diagnostic_labs", "diagnostic_tests",
        "specialities", "hospital_specialities", "doctor_specialities", "opds",
    }
    assert expected.issubset(table_names), f"Missing tables: {expected - table_names}"


def test_hospital_model_columns():
    """Hospital model has all required columns with correct nullability."""
    columns = {c.name: c for c in Hospital.__table__.columns}

    required_not_null = ["id", "name", "slug", "address", "city", "state",
                         "verification_status", "is_active", "created_at", "updated_at"]
    for col_name in required_not_null:
        assert col_name in columns, f"Hospital missing column: {col_name}"
        assert not columns[col_name].nullable, f"Hospital.{col_name} should be NOT NULL"

    nullable_columns = ["description", "hospital_type", "locality", "pincode",
                        "latitude", "longitude", "phone", "email", "website",
                        "operating_hours"]
    for col_name in nullable_columns:
        assert col_name in columns, f"Hospital missing column: {col_name}"
        assert columns[col_name].nullable, f"Hospital.{col_name} should be nullable"


def test_hospital_defaults_and_constraints():
    """Hospital has correct defaults and check constraints."""
    assert Hospital.city.server_default is not None
    assert Hospital.state.server_default is not None
    assert Hospital.verification_status.server_default is not None
    assert Hospital.is_active.server_default is not None

    constraint_names = [c.name for c in Hospital.__table__.constraints
                        if hasattr(c, 'name') and c.name]
    assert any("verification_status" in n for n in constraint_names)
    assert any("latitude" in n for n in constraint_names)
    assert any("longitude" in n for n in constraint_names)


def test_hospital_slug_unique():
    """Hospital.slug has a unique constraint."""
    slug_col = Hospital.__table__.c.slug
    assert slug_col.unique, "Hospital.slug should be unique"


def test_doctor_model_columns():
    """Doctor model has all required columns."""
    columns = {c.name: c for c in Doctor.__table__.columns}

    required_not_null = ["id", "full_name", "slug", "verification_status",
                         "is_active", "created_at", "updated_at"]
    for col_name in required_not_null:
        assert col_name in columns, f"Doctor missing column: {col_name}"
        assert not columns[col_name].nullable, f"Doctor.{col_name} should be NOT NULL"

    nullable_columns = ["qualifications", "specializations", "experience_years",
                        "languages", "consultation_fee", "phone", "hospital_id"]
    for col_name in nullable_columns:
        assert col_name in columns, f"Doctor missing column: {col_name}"
        assert columns[col_name].nullable, f"Doctor.{col_name} should be nullable"


def test_doctor_foreign_key():
    """Doctor.hospital_id references hospitals.id."""
    fks = [fk for fk in Doctor.__table__.foreign_keys]
    hospital_fk = [fk for fk in fks if "hospitals.id" in str(fk.target_fullname)]
    assert hospital_fk, "Doctor should have a foreign key to hospitals.id"


def test_doctor_constraints():
    """Doctor has check constraints for non-negative values and valid status."""
    constraint_names = [c.name for c in Doctor.__table__.constraints
                        if hasattr(c, 'name') and c.name]
    assert any("experience_years" in n for n in constraint_names)
    assert any("consultation_fee" in n for n in constraint_names)
    assert any("verification_status" in n for n in constraint_names)


def test_diagnostic_lab_model_columns():
    """DiagnosticLab model has all required columns."""
    columns = {c.name: c for c in DiagnosticLab.__table__.columns}

    required_not_null = ["id", "name", "slug", "address", "city", "state",
                         "verification_status", "is_active", "created_at", "updated_at"]
    for col_name in required_not_null:
        assert col_name in columns, f"DiagnosticLab missing column: {col_name}"
        assert not columns[col_name].nullable, f"DiagnosticLab.{col_name} should be NOT NULL"

    nullable_columns = ["description", "locality", "phone"]
    for col_name in nullable_columns:
        assert col_name in columns, f"DiagnosticLab missing column: {col_name}"
        assert columns[col_name].nullable, f"DiagnosticLab.{col_name} should be nullable"


def test_diagnostic_test_model_columns():
    """DiagnosticTest model has all required columns."""
    columns = {c.name: c for c in DiagnosticTest.__table__.columns}

    required_not_null = ["id", "lab_id", "name", "availability_status",
                         "created_at", "updated_at"]
    for col_name in required_not_null:
        assert col_name in columns, f"DiagnosticTest missing column: {col_name}"
        assert not columns[col_name].nullable, f"DiagnosticTest.{col_name} should be NOT NULL"

    nullable_columns = ["description", "price", "preparation_instructions"]
    for col_name in nullable_columns:
        assert col_name in columns, f"DiagnosticTest missing column: {col_name}"
        assert columns[col_name].nullable, f"DiagnosticTest.{col_name} should be nullable"


def test_diagnostic_test_foreign_key():
    """DiagnosticTest.lab_id references diagnostic_labs.id."""
    fks = [fk for fk in DiagnosticTest.__table__.foreign_keys]
    lab_fk = [fk for fk in fks if "diagnostic_labs.id" in str(fk.target_fullname)]
    assert lab_fk, "DiagnosticTest should have a foreign key to diagnostic_labs.id"


def test_diagnostic_test_price_constraint():
    """DiagnosticTest has a non-negative price check constraint."""
    constraint_names = [c.name for c in DiagnosticTest.__table__.constraints
                        if hasattr(c, 'name') and c.name]
    assert any("price" in n for n in constraint_names)


def test_hospital_doctor_relationship():
    """Hospital-doctor relationship is bidirectional."""
    assert hasattr(Hospital, "doctors")
    assert hasattr(Doctor, "hospital")


def test_diagnostic_lab_test_relationship():
    """DiagnosticLab-diagnostic test relationship is bidirectional."""
    assert hasattr(DiagnosticLab, "tests")
    assert hasattr(DiagnosticTest, "lab")


def test_verification_status_values():
    """Verification status supports the required values on all models."""
    valid_statuses = {"unverified", "pending", "verified", "rejected"}
    for model in [Hospital, Doctor, DiagnosticLab]:
        constraint_names = [c.name for c in model.__table__.constraints
                            if hasattr(c, 'name') and c.name]
        status_constraint = [n for n in constraint_names if "verification_status" in n]
        assert status_constraint, f"{model.__name__} missing verification_status constraint"


def test_provider_provenance_constraints_and_defaults():
    """Existing providers default to unverified with source data left unknown."""
    for model in [Hospital, Doctor, DiagnosticLab, OPD]:
        columns = model.__table__.columns
        assert columns.source.nullable
        assert columns.source_url.nullable
        assert columns.verified_at.nullable
        assert columns.is_verified.server_default is not None
        assert columns.is_demo.server_default is not None
        checks = {constraint.name for constraint in model.__table__.constraints
                  if isinstance(constraint, CheckConstraint)}
        assert f"chk_{model.__tablename__}_verified_provenance" in checks
        assert f"chk_{model.__tablename__}_demo_unverified" in checks


def test_speciality_join_keys_and_opd_hospital_link():
    assert HospitalSpeciality.__table__.primary_key.columns.keys() == ["hospital_id", "speciality_id"]
    assert DoctorSpeciality.__table__.primary_key.columns.keys() == ["doctor_id", "speciality_id"]
    assert OPD.__table__.c.hospital_id.nullable
    assert any(fk.target_fullname == "hospitals.id" for fk in OPD.__table__.c.hospital_id.foreign_keys)
    assert hasattr(Hospital, "specialities") and hasattr(Doctor, "specialities")
