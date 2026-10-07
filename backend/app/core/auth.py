import time
from typing import Dict, List, Optional, Set
from fastapi import Depends, HTTPException, Request, Response, status
import httpx
import jwt
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.core.security import generate_csrf_token, sign_session_payload, verify_csrf_token, verify_session_payload

ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN = 'viewer', 'analyst', 'admin'
ALL_ROLES = {ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN}
ROLE_HIERARCHY: Dict[str, Set[str]] = {ROLE_ADMIN: {ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER}, ROLE_ANALYST: {ROLE_ANALYST, ROLE_VIEWER}, ROLE_VIEWER: {ROLE_VIEWER}}
DEMO_PROFILES = {
    'admin': {'user_id': 'usr-demo-admin', 'email': 'ryandtvo@gmail.com', 'name': 'Ryan Vo (Lead Scientist)', 'roles': [ROLE_ADMIN]},
    'analyst': {'user_id': 'usr-demo-analyst', 'email': 'analyst@ryanvo.ai', 'name': 'Alex Chen (ML Analyst)', 'roles': [ROLE_ANALYST]},
    'viewer': {'user_id': 'usr-demo-viewer', 'email': 'viewer@ryanvo.ai', 'name': 'Sam Taylor (Research Observer)', 'roles': [ROLE_VIEWER]},
}
_oidc_cache: Dict[str, dict] = {}
_cache_expiry: float = 0.0

class UserSession(BaseModel):
    user_id: str
    email: str
    name: str
    roles: List[str]
    session_id: str
    is_demo: bool = False

async def fetch_oidc_discovery() -> dict:
    global _oidc_cache, _cache_expiry
    if not settings.oidc_discovery_url:
        raise HTTPException(status_code=500, detail='OIDC discovery URL is not configured on server')
    now = time.time()
    if 'doc' in _oidc_cache and now < _cache_expiry:
        return _oidc_cache['doc']
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(settings.oidc_discovery_url)
            resp.raise_for_status()
            doc = resp.json()
            _oidc_cache['doc'] = doc
            _cache_expiry = now + 300
            return doc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Unable to reach upstream OIDC discovery endpoint: {str(exc)}')

async def validate_oidc_id_token(id_token: str, expected_nonce: Optional[str]=None) -> dict:
    doc = await fetch_oidc_discovery()
    jwks_uri, issuer = doc.get('jwks_uri'), doc.get('issuer')
    if not jwks_uri or not issuer:
        raise HTTPException(status_code=500, detail='Malformed OIDC discovery metadata')
    try:
        key = jwt.PyJWKClient(jwks_uri).get_signing_key_from_jwt(id_token).key
        payload = jwt.decode(id_token, key, algorithms=['RS256'], issuer=issuer, audience=settings.oidc_client_id, options={'require': ['exp', 'iss', 'aud', 'sub']})
        if expected_nonce and payload.get('nonce') != expected_nonce:
            raise HTTPException(status_code=401, detail='OIDC nonce mismatch')
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f'Invalid OIDC token: {str(e)}')

def extract_user_roles(claims: dict) -> List[str]:
    roles = {r for r in claims.get('roles', []) if r in ALL_ROLES}
    roles |= {r for r in claims.get('realm_access', {}).get('roles', []) if r in ALL_ROLES}
    roles |= {r for r in claims.get('resource_access', {}).get(settings.oidc_client_id, {}).get('roles', []) if r in ALL_ROLES}
    return list(roles) or [ROLE_VIEWER]

def get_current_user_optional(request: Request) -> Optional[UserSession]:
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        return None
    p = verify_session_payload(cookie)
    return UserSession(user_id=p.get('user_id', 'usr-anon'), email=p.get('email', 'unknown@domain'), name=p.get('name', 'User'), roles=p.get('roles', [ROLE_VIEWER]), session_id=p.get('session_id', ''), is_demo=p.get('is_demo', False)) if p else None

def validate_csrf(request: Request, user: UserSession) -> None:
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        csrf = request.headers.get('X-CSRF-Token')
        if not csrf or not verify_csrf_token(csrf, user.session_id):
            raise HTTPException(status_code=403, detail='Invalid or missing CSRF token')

def get_current_user(request: Request) -> UserSession:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail='Authentication required. Please log in via OIDC or demo mode.')
    validate_csrf(request, user)
    return user

def require_role(required_role: str):
    def role_dependency(user: UserSession=Depends(get_current_user)) -> UserSession:
        perms = {p for r in user.roles for p in ROLE_HIERARCHY.get(r, {r})}
        if required_role not in perms:
            raise HTTPException(status_code=403, detail=f"Forbidden: '{required_role}' permission required for this resource.")
        return user
    return role_dependency

def set_user_session_cookie(response: Response, user_session: dict) -> str:
    token = sign_session_payload(user_session, max_age=settings.session_max_age_seconds)
    response.set_cookie(key=settings.session_cookie_name, value=token, max_age=settings.session_max_age_seconds, httponly=True, samesite=settings.session_cookie_samesite, secure=settings.session_cookie_secure, path='/')
    return generate_csrf_token(user_session['session_id'])

def clear_user_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path='/', samesite=settings.session_cookie_samesite)
