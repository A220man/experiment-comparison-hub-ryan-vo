"""Pytest fixtures for database, clients, and mock sessions."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEMO_MODE"] = "true"
os.environ["HOST"] = "127.0.0.1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.app.core.auth import (
    DEMO_PROFILES,
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_VIEWER,
    set_user_session_cookie,
)
from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.core.security import generate_csrf_token
from backend.app.main import app

# In-memory test SQLite engine
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_authenticated_client(client: TestClient, role: str) -> tuple[TestClient, dict]:
    """Helper to simulate an authenticated user session with CSRF headers."""
    resp = client.post("/api/v1/auth/demo-switch", json={"profile": role})
    assert resp.status_code == 200
    data = resp.json()
    csrf_token = data["csrf_token"]
    headers = {"X-CSRF-Token": csrf_token}
    return client, headers


@pytest.fixture
def viewer_client(client):
    c, headers = create_authenticated_client(client, "viewer")
    return c, headers


@pytest.fixture
def analyst_client(client):
    c, headers = create_authenticated_client(client, "analyst")
    return c, headers


@pytest.fixture
def admin_client(client):
    c, headers = create_authenticated_client(client, "admin")
    return c, headers
