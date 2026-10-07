import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = 'Experiment Comparison Hub'
    app_version: str = '0.1.0'
    environment: str = 'development'
    host: str = '127.0.0.1'
    port: int = 8000
    database_url: str = 'sqlite:///./storage/experiments.db'
    demo_mode: bool = False
    session_secret_key: str = 'development-only-session-secret-change-in-production-min-32-chars'
    csrf_secret_key: str = 'development-only-csrf-secret-change-in-production-min-32-chars'
    session_cookie_name: str = 'ech_session'
    session_cookie_secure: bool = False
    session_cookie_samesite: str = 'lax'
    session_max_age_seconds: int = 86400
    oidc_discovery_url: Optional[str] = None
    oidc_client_id: str = 'experiment-hub-client'
    oidc_client_secret: Optional[str] = None
    oidc_redirect_uri: str = 'http://127.0.0.1:8000/api/v1/auth/callback'
    llm_api_key: Optional[str] = None
    llm_provider: str = 'openai'
    llm_model: str = 'qwen3.8-27b'
    llm_base_url: str = 'https://llm.chris-vo.com/v1'
    llm_timeout_seconds: float = 15.0
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    @field_validator('demo_mode')
    @classmethod
    def validate_demo_mode_safety(cls, demo_mode: bool, info) -> bool:
        env = (info.data.get('environment') or os.environ.get('ENVIRONMENT', 'development')).lower()
        host = (info.data.get('host') or os.environ.get('HOST', '127.0.0.1')).lower()
        if demo_mode:
            if env in ('production', 'prod'):
                raise ValueError('SECURITY VIOLATION: Demo mode is strictly refused in production environment.')
            if host not in ('127.0.0.1', 'localhost', 'testserver'):
                raise ValueError(f'SECURITY VIOLATION: Demo mode can only bind to localhost/127.0.0.1 (got {host}).')
        return demo_mode

settings = Settings()
