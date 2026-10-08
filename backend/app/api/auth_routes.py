import secrets, urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import httpx
from backend.app.core.auth import DEMO_PROFILES, UserSession, clear_user_session_cookie, extract_user_roles, fetch_oidc_discovery, get_current_user, get_current_user_optional, set_user_session_cookie, validate_oidc_id_token
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
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce_pair()
    _pending_oauth_states[state] = {'nonce': nonce, 'verifier': verifier}
    params = {'client_id': settings.oidc_client_id, 'response_type': 'code', 'scope': 'openid email profile', 'redirect_uri': settings.oidc_redirect_uri, 'state': state, 'nonce': nonce, 'code_challenge': challenge, 'code_challenge_method': 'S256'}
    return {'authorization_url': f'{auth_endpoint}?{urllib.parse.urlencode(params)}', 'state': state}

@router.get('/callback')
async def oidc_callback(response: Response, code: str = '', state: str = '', error: str = '', error_description: str = ''):
    if error:
        raise HTTPException(status_code=400, detail=f'OIDC IdP error: {error} - {error_description}'.strip(' -'))
    if not state or state not in _pending_oauth_states:
        raise HTTPException(status_code=400, detail='Invalid or expired OAuth state parameter.')
    if not code:
        raise HTTPException(status_code=400, detail='Missing authorization code from IdP callback.')
    meta = _pending_oauth_states.pop(state)
    verifier, nonce = meta.get('verifier'), meta.get('nonce')
    doc = await fetch_oidc_discovery()
    tok_ep = doc.get('token_endpoint')
    if not tok_ep:
        raise HTTPException(status_code=500, detail='Missing token_endpoint in OIDC discovery')
    data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': settings.oidc_redirect_uri, 'client_id': settings.oidc_client_id, 'code_verifier': verifier}
    if settings.oidc_client_secret: data['client_secret'] = settings.oidc_client_secret
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tr = await client.post(tok_ep, data=data)
            if tr.is_error: raise HTTPException(status_code=400, detail=f'Token exchange failed: {tr.text}')
            tokens = tr.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f'Token endpoint unreachable: {exc}')
    id_token = tokens.get('id_token')
    if not id_token: raise HTTPException(status_code=400, detail='No ID token returned by token endpoint.')
    claims = await validate_oidc_id_token(id_token, expected_nonce=nonce)
    uid = claims.get('sub', f'usr-{secrets.token_hex(6)}')
    em = claims.get('email', f'{uid}@idp.user')
    u = {'user_id': uid, 'email': em, 'name': claims.get('name') or em, 'roles': extract_user_roles(claims), 'session_id': f'oidc-sess-{secrets.token_hex(8)}', 'is_demo': False}
    csrf = set_user_session_cookie(response, u)
    return {'status': 'authenticated', 'user': u, 'csrf_token': csrf}

@router.get('/me', response_model=UserResponse)
def get_me(user: UserSession = Depends(get_current_user)):
    return UserResponse(user_id=user.user_id, email=user.email, name=user.name, roles=user.roles, session_id=user.session_id, is_demo=user.is_demo)

@router.get('/csrf-token')
def get_csrf_token(request: Request):
    u = get_current_user_optional(request)
    return {'csrf_token': generate_csrf_token(u.session_id if u else 'anon-session')}

@router.post('/logout')
def logout(response: Response, user: UserSession = Depends(get_current_user)):
    clear_user_session_cookie(response)
    return {'status': 'logged_out', 'message': 'Session invalidated successfully.'}

@router.post('/demo-switch')
def demo_switch(req: DemoSwitchRequest, response: Response):
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Demo mode is disabled. Production requires OIDC identity provider login.')
    p = DEMO_PROFILES.get(req.profile)
    if not p: raise HTTPException(status_code=400, detail='Unknown demo profile')
    u = {'user_id': p['user_id'], 'email': p['email'], 'name': p['name'], 'roles': p['roles'], 'session_id': f'demo-sess-{secrets.token_hex(8)}', 'is_demo': True}
    csrf = set_user_session_cookie(response, u)
    return {'status': 'authenticated', 'user': u, 'csrf_token': csrf}
