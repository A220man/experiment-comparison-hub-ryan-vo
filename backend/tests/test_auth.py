"""Authentication, CSRF validation, and Role-Based Access Control tests."""

import pytest
from pydantic import ValidationError
from backend.app.core.config import Settings


def test_unauthenticated_request_rejected(client):
    """Unauthenticated access to protected data endpoints must return 401."""
    resp = client.get("/api/v1/experiments")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_role_denial_viewer_cannot_create_experiment(viewer_client):
    """A user with only viewer role must be denied with 403 when trying to create an experiment."""
    client, headers = viewer_client
    payload = {"name": "Test Experiment", "domain": "ai-ml"}
    resp = client.post("/api/v1/experiments", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "analyst" in resp.json()["detail"].lower()


def test_role_denial_analyst_cannot_view_audit_logs(analyst_client):
    """An analyst cannot access admin-only audit log endpoint."""
    client, headers = analyst_client
    resp = client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()


def test_csrf_token_enforcement(client):
    """Mutating write without valid CSRF header must be rejected with 403."""
    # Authenticate as analyst
    switch_res = client.post("/api/v1/auth/demo-switch", json={"profile": "analyst"})
    assert switch_res.status_code == 200

    # Attempt POST without X-CSRF-Token header
    resp = client.post(
        "/api/v1/experiments",
        json={"name": "CSRF Attack Attempt", "domain": "ai-ml"},
    )
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]

    # Attempt POST with invalid CSRF token
    resp_invalid = client.post(
        "/api/v1/experiments",
        json={"name": "CSRF Attack Attempt", "domain": "ai-ml"},
        headers={"X-CSRF-Token": "invalid:nonce:fake-signature"},
    )
    assert resp_invalid.status_code == 403
    assert "CSRF" in resp_invalid.json()["detail"]


def test_demo_mode_switch_login_and_logout(client):
    """Demo switcher assigns session cookie and allows explicit logout."""
    login_resp = client.post("/api/v1/auth/demo-switch", json={"profile": "admin"})
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["user"]["email"] == "ryandtvo@gmail.com"
    csrf_token = data["csrf_token"]

    # Verify session is authenticated
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "ryandtvo@gmail.com"

    # Explicit logout
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert logout_resp.status_code == 200

    # Subsequent request should be 401
    after_me = client.get("/api/v1/auth/me")
    assert after_me.status_code == 401


def test_demo_mode_startup_refusal_in_production():
    """Safety guarantee: System strictly refuses to initialize demo mode in production or non-localhost host."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(demo_mode=True, environment="production", host="127.0.0.1")
    assert "strictly refused in production" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info_host:
        Settings(demo_mode=True, environment="development", host="0.0.0.0")
    assert "Demo mode can only bind to localhost" in str(exc_info_host.value)
