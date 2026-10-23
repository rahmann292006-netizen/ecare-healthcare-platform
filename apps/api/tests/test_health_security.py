"""DB-free failure-path coverage for the database health endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_db_failure_does_not_expose_connection_url(capsys):
    fake_url = "postgresql+psycopg://user:SECRET@host/db"

    with patch("app.main.engine.connect", side_effect=RuntimeError(fake_url)):
        response = TestClient(app).get("/health/db")

    output = capsys.readouterr().out
    assert response.status_code == 503
    assert response.json() == {"detail": "Database not reachable"}
    assert "SECRET" not in response.text
    assert "SECRET" not in output
    assert fake_url not in response.text
    assert fake_url not in output
