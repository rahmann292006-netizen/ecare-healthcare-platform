"""Offline checks for the operational-status migration DDL."""

import importlib.util
from io import StringIO
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "c8f1a2d4e6b0_add_provider_operational_status.py"
)
spec = importlib.util.spec_from_file_location("operational_status_migration", MIGRATION_PATH)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def _render(operation):
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql",
        opts={"as_sql": True, "output_buffer": output},
    )
    with Operations.context(context):
        operation()
    return output.getvalue()


def test_upgrade_adds_unknown_default_and_constrained_status_to_every_provider():
    sql = _render(migration.upgrade)

    for table in ("hospitals", "doctors", "diagnostic_labs", "opds"):
        assert f"ALTER TABLE {table} ADD COLUMN operational_status VARCHAR(30) DEFAULT 'unknown' NOT NULL" in sql
        assert f"chk_{table}_operational_status" in sql
    assert "operational_status IN ('unknown', 'operational', 'not_operational')" in sql
    assert "ALTER TABLE hospitals ALTER COLUMN emergency_services DROP NOT NULL" in sql
    assert "ALTER TABLE diagnostic_labs ALTER COLUMN home_sample_collection DROP NOT NULL" in sql


def test_downgrade_documents_unknown_service_value_collapse():
    sql = _render(migration.downgrade)

    assert "emergency_services = false WHERE emergency_services IS NULL" in sql
    assert "home_sample_collection = false WHERE home_sample_collection IS NULL" in sql
    assert "DROP COLUMN operational_status" in sql
