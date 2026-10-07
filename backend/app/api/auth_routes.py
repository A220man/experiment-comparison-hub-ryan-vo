import secrets
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from backend.app.core.auth import DEMO_PROFILES, ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, UserSession, clear_user_session_cookie, extract_user_roles, fetch_oidc_discovery, get_current_user, get_current_user_optional, set_user_session_cookie, validate_oidc_id_token
from backend.app.core.config import settings
from backend.app.core.security import generate_csrf_token, generate_pkce_pair
from backend.app.models.schemas import DemoSwitchRequest, UserResponse
router = APIRouter(prefix='/auth', tags=['Authentication'])
_pending_oauth_states = {}

@router.get('/login')
async def oidc_login():
    if not settings.oidc_discovery_url:
        if settings.demo_mode:
            raise HTTPException(status_code=400, detail='OIDC discovery not configured. Demo mode is active: use /api/v1/auth/demo-switch to login.')
        raise HTTPException(status_code=500, detail='OIDC discovery URL is not configured.')
    doc = await fetch_oidc_discovery()
    auth_endpoint = doc.get('authorization_endpoint')
    if not auth_endpoint:
        raise HTTPException(status_code=500, detail='Authorization endpoint missing in OIDC discovery')
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce_pair()
    _pending_oauth_states[state] = {'nonce': nonce, 'verifier': verifier}
    params = {'client_id': settings.oidc_client_id, 'response_type': 'code', 'scope': 'openid email profile', 'redirect_uri': settings.oidc_redirect_uri, 'state': state, 'nonce': nonce, 'code_challenge': challenge, 'code_challenge_method': 'S256'}
    redirect_url = f'{auth_endpoint}?{urllib.parse.urlencode(params)}'
    return {'authorization_url': redirect_url, 'state': state}

@router.get('/me', response_model=UserResponse)
def get_me(request: Request, user: UserSession=Depends(get_current_user)):
    return UserResponse(user_id=user.user_id, email=user.email, name=user.name, roles=user.roles, session_id=user.session_id, is_demo=user.is_demo)

@router.get('/csrf-token')
def get_csrf_token(request: Request):
    user = get_current_user_optional(request)
    session_id = user.session_id if user else 'anon-session'
    token = generate_csrf_token(session_id)
    return {'csrf_token': token}

@router.post('/logout')
def logout(response: Response, user: UserSession=Depends(get_current_user)):
    clear_user_session_cookie(response)
    return {'status': 'logged_out', 'message': 'Session invalidated successfully.'}

@router.post('/demo-switch')
def demo_switch(req: DemoSwitchRequest, response: Response):
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Demo mode is disabled. Production requires OIDC identity provider login.')
    profile_data = DEMO_PROFILES.get(req.profile)
    if not profile_data:
        raise HTTPException(status_code=400, detail='Unknown demo profile')
    session_id = f'demo-sess-{secrets.token_hex(8)}'
    user_dict = {'user_id': profile_data['user_id'], 'email': profile_data['email'], 'name': profile_data['name'], 'roles': profile_data['roles'], 'session_id': session_id, 'is_demo': True}
    csrf_token = set_user_session_cookie(response, user_dict)
    return {'status': 'authenticated', 'user': user_dict, 'csrf_token': csrf_token}
