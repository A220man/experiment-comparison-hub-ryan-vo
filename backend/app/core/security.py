import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from backend.app.core.config import settings

def generate_pkce_pair() -> Tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return (verifier, challenge)

def sign_session_payload(payload: Dict[str, Any], max_age: int=86400) -> str:
    data = dict(payload)
    data['_exp'] = int(time.time()) + max_age
    raw_json = json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8')
    b64_data = base64.urlsafe_b64encode(raw_json).decode('ascii')
    signature = hmac.new(settings.session_secret_key.encode('utf-8'), b64_data.encode('ascii'), hashlib.sha256).hexdigest()
    return f'{b64_data}.{signature}'

def verify_session_payload(token: str) -> Optional[Dict[str, Any]]:
    if not token or '.' not in token:
        return None
    try:
        b64_data, received_sig = token.rsplit('.', 1)
        expected_sig = hmac.new(settings.session_secret_key.encode('utf-8'), b64_data.encode('ascii'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(received_sig, expected_sig):
            return None
        raw_json = base64.urlsafe_b64decode(b64_data.encode('ascii')).decode('utf-8')
        data = json.loads(raw_json)
        if '_exp' in data and time.time() > data['_exp']:
            return None
        return data
    except Exception:
        return None

def generate_csrf_token(session_id: str) -> str:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    message = f'{session_id}:{timestamp}:{nonce}'.encode('utf-8')
    signature = hmac.new(settings.csrf_secret_key.encode('utf-8'), message, hashlib.sha256).hexdigest()
    return f'{timestamp}:{nonce}:{signature}'

def verify_csrf_token(token: str, session_id: str, max_age: int=86400) -> bool:
    if not token or not session_id:
        return False
    parts = token.split(':')
    if len(parts) != 3:
        return False
    timestamp_str, nonce, received_sig = parts
    try:
        timestamp = int(timestamp_str)
        if time.time() - timestamp > max_age or time.time() < timestamp - 60:
            return False
        message = f'{session_id}:{timestamp_str}:{nonce}'.encode('utf-8')
        expected_sig = hmac.new(settings.csrf_secret_key.encode('utf-8'), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(received_sig, expected_sig)
    except Exception:
        return False

def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def calculate_file_sha256(file_path: str) -> Optional[str]:
    if not os.path.exists(file_path):
        return None
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while (chunk := f.read(65536)):
            hasher.update(chunk)
    return hasher.hexdigest()
