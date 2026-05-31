"""API smoke/integration tests via FastAPI TestClient.

Requires the full backend stack (FastAPI, SQLAlchemy, etc.). Uses an in-memory
SQLite database so it runs without MySQL. Skipped if dependencies are absent.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

# Point the app at an in-memory SQLite DB before importing it.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "service" in res.json()


def test_health_liveness(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_version(client):
    res = client.get("/api/v1/version")
    assert res.status_code == 200
    assert "version" in res.json()


def test_openapi_schema_lists_core_routes(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/search" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/billing/plans" in paths
    assert any(p.startswith("/api/v1/admin") for p in paths)


def test_search_requires_query(client):
    # Missing required 'q' -> 422 validation error.
    res = client.get("/api/v1/search")
    assert res.status_code == 422


def test_protected_route_requires_auth(client):
    res = client.get("/api/v1/me/saved")
    assert res.status_code == 401
