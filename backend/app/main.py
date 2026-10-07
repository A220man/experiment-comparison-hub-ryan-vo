import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlalchemy
from backend.app.api.analysis_routes import router as analysis_router
from backend.app.api.artifact_routes import router as artifact_router
from backend.app.api.audit_routes import router as audit_router
from backend.app.api.auth_routes import router as auth_router
from backend.app.api.experiment_routes import router as experiment_router
from backend.app.api.export_routes import router as export_router
from backend.app.api.run_routes import router as run_router
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('experiment_hub')

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment != 'testing':
        init_db()
    if settings.demo_mode:
        if settings.environment.lower() in ('production', 'prod'):
            raise RuntimeError('CRITICAL SECURITY ERROR: Demo mode cannot run in production environment.')
        logger.warning('*** DEMO MODE ACTIVE: Local simulated personas enabled. Never use in production. ***')
    yield

app = FastAPI(title=settings.app_name, version=settings.app_version, description='Track experiment runs, hyperparameters and artifacts, calculate Pareto frontiers and compare metrics across seeds.', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:8000', 'http://localhost:8000'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.middleware('http')
async def security_headers_middleware(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.update({'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'strict-origin-when-cross-origin', 'X-XSS-Protection': '1; mode=block'})
    return resp

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f'Unhandled error processing {request.method} {request.url.path}: {str(exc)}', exc_info=True)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={'detail': 'An internal server error occurred. Transaction rolled back.'})

@app.get('/healthz', tags=['Health'])
def health_check():
    return {'status': 'ok', 'app': settings.app_name, 'version': settings.app_version}

@app.get('/readyz', tags=['Health'])
def readiness_check():
    try:
        with SessionLocal() as db:
            db.execute(sqlalchemy.text('SELECT 1'))
        return {'status': 'ready', 'database': 'connected'}
    except Exception as exc:
        return JSONResponse(status_code=503, content={'status': 'unready', 'error': str(exc)})

for r in (auth_router, experiment_router, run_router, artifact_router, analysis_router, audit_router, export_router):
    app.include_router(r, prefix='/api/v1')
