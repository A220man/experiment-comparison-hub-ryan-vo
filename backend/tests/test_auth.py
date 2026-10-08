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


def test_oidc_login_and_callback_protocol_flow(client, monkeypatch):
    """Complete OIDC protocol fixture: login -> PKCE/state -> IdP error -> PKCE rejection -> valid callback -> authorized API request."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt, time
    from backend.app.core.config import settings
    from backend.app.api.auth_routes import _pending_oauth_states

    mock_discovery = {
        "issuer": "https://idp.local/realms/experiment-hub",
        "authorization_endpoint": "https://idp.local/auth",
        "token_endpoint": "https://idp.local/token",
        "jwks_uri": "https://idp.local/jwks",
    }
    monkeypatch.setattr(settings, "oidc_discovery_url", "https://idp.local/.well-known/openid-configuration")
    monkeypatch.setattr(settings, "oidc_client_id", "experiment-hub-client")

    async def mock_fetch_discovery():
        return mock_discovery

    monkeypatch.setattr("backend.app.api.auth_routes.fetch_oidc_discovery", mock_fetch_discovery)
    monkeypatch.setattr("backend.app.core.auth.fetch_oidc_discovery", mock_fetch_discovery)

    # 1. Login endpoint generates authorization URL with state, nonce, PKCE
    login_resp = client.get("/api/v1/auth/login")
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "authorization_url" in login_data
    state = login_data["state"]
    assert state in _pending_oauth_states
    saved_verifier = _pending_oauth_states[state]["verifier"]
    assert len(saved_verifier) >= 43

    # 2. IdP error handling
    err_resp = client.get(f"/api/v1/auth/callback?error=access_denied&error_description=User+cancelled&state={state}")
    assert err_resp.status_code == 400
    assert "access_denied" in err_resp.json()["detail"]

    # 3. State rejection: invalid or unknown state
    bad_state_resp = client.get("/api/v1/auth/callback?code=fake-auth-code&state=nonexistent-state-12345")
    assert bad_state_resp.status_code == 400
    assert "Invalid or expired OAuth state parameter" in bad_state_resp.json()["detail"]

    # Missing state
    missing_state_resp = client.get("/api/v1/auth/callback?code=fake-auth-code")
    assert missing_state_resp.status_code == 400

    # Missing code with valid state
    missing_code_resp = client.get(f"/api/v1/auth/callback?state={state}")
    assert missing_code_resp.status_code == 400
    assert "Missing authorization code" in missing_code_resp.json()["detail"]

    # 4. PKCE rejection at token endpoint
    login_resp2 = client.get("/api/v1/auth/login")
    state2 = login_resp2.json()["state"]

    class MockFailedTokenClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, data=None):
            class MockResponse:
                is_error = True
                status_code = 400
                text = "invalid_grant: PKCE verification failed"
            return MockResponse()

    monkeypatch.setattr("backend.app.api.auth_routes.httpx.AsyncClient", MockFailedTokenClient)
    pkce_fail_resp = client.get(f"/api/v1/auth/callback?code=code-abc&state={state2}")
    assert pkce_fail_resp.status_code == 400
    assert "Token exchange failed" in pkce_fail_resp.json()["detail"]

    # 5. Successful OIDC login & callback
    login_resp3 = client.get("/api/v1/auth/login")
    state3 = login_resp3.json()["state"]
    nonce3 = _pending_oauth_states[state3]["nonce"]

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    now = int(time.time())
    token_claims = {
        "sub": "usr-oidc-analyst-99",
        "email": "analyst@ryanvo.ai",
        "name": "Ryan Vo Analyst",
        "roles": ["analyst"],
        "iss": "https://idp.local/realms/experiment-hub",
        "aud": "experiment-hub-client",
        "exp": now + 3600,
        "iat": now,
        "nonce": nonce3,
    }
    signed_id_token = jwt.encode(token_claims, private_key, algorithm="RS256", headers={"kid": "key-1"})

    class MockSuccessTokenClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, data=None):
            assert "code_verifier" in data
            assert len(data["code_verifier"]) >= 43
            class MockResponse:
                is_error = False
                status_code = 200
                def json(self):
                    return {"id_token": signed_id_token, "access_token": "acc-tok", "token_type": "Bearer"}
            return MockResponse()

    class MockSigningKey:
        def __init__(self, key):
            self.key = key

    monkeypatch.setattr("backend.app.api.auth_routes.httpx.AsyncClient", MockSuccessTokenClient)
    monkeypatch.setattr(jwt.PyJWKClient, "get_signing_key_from_jwt", lambda self, tok: MockSigningKey(public_key))

    cb_resp = client.get(f"/api/v1/auth/callback?code=valid-auth-code&state={state3}")
    assert cb_resp.status_code == 200
    cb_data = cb_resp.json()
    assert cb_data["status"] == "authenticated"
    assert cb_data["user"]["email"] == "analyst@ryanvo.ai"
    assert "analyst" in cb_data["user"]["roles"]
    csrf_token = cb_data["csrf_token"]
    assert csrf_token

    # 6. Token propagation into authorized requests
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "analyst@ryanvo.ai"

    create_exp_resp = client.post(
        "/api/v1/experiments",
        json={"name": "OIDC Authenticated Experiment", "domain": "ai-ml"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert create_exp_resp.status_code == 201
    assert create_exp_resp.json()["name"] == "OIDC Authenticated Experiment"

