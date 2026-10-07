import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_ANALYST, ROLE_VIEWER, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.schemas import RunBatchCreate, RunCreate, RunDiffResponse, RunListResponse, RunResponse, RunUpdate
from backend.app.services import experiment_service

router = APIRouter(prefix='/runs', tags=['Runs'])

@router.get('', response_model=RunListResponse)
def list_runs(experiment_id: str=Query(..., description='Target experiment ID'), page: int=Query(default=1, ge=1), page_size: int=Query(default=50, ge=1, le=200), variant_name: Optional[str]=None, seed: Optional[int]=None, tag: Optional[str]=None, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    items, total = experiment_service.list_runs(db, experiment_id=experiment_id, page=page, page_size=page_size, variant_name=variant_name, seed=seed, tag=tag)
    pages = math.ceil(total / page_size) if total > 0 else 1
    return RunListResponse(items=[RunResponse.model_validate(r) for r in items], total=total, page=page, page_size=page_size, pages=pages)

@router.post('', response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(data: RunCreate, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    if not experiment_service.get_experiment_by_id(db, data.experiment_id):
        raise HTTPException(status_code=404, detail=f"Experiment '{data.experiment_id}' not found")
    ip = request.client.host if request.client else None
    return RunResponse.model_validate(experiment_service.create_run(db, data, user.email, ip))

@router.post('/batch', response_model=List[RunResponse], status_code=status.HTTP_201_CREATED)
def create_runs_batch(data: RunBatchCreate, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    if not experiment_service.get_experiment_by_id(db, data.experiment_id):
        raise HTTPException(status_code=404, detail=f"Experiment '{data.experiment_id}' not found")
    ip = request.client.host if request.client else None
    return [RunResponse.model_validate(experiment_service.create_run(db, r, user.email, ip)) for r in data.runs]

@router.get('/diff', response_model=RunDiffResponse)
def diff_runs_endpoint(base_run_id: str=Query(...), target_run_id: str=Query(...), db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    b = experiment_service.get_run_by_id(db, base_run_id)
    t = experiment_service.get_run_by_id(db, target_run_id)
    if not b or not t:
        raise HTTPException(status_code=404, detail='Run not found')
    return experiment_service.diff_runs(b, t)

@router.get('/{run_id}', response_model=RunResponse)
def get_run(run_id: str, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    r = experiment_service.get_run_by_id(db, run_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return RunResponse.model_validate(r)

@router.put('/{run_id}', response_model=RunResponse)
def update_run(run_id: str, data: RunUpdate, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    r = experiment_service.get_run_by_id(db, run_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    ip = request.client.host if request.client else None
    return RunResponse.model_validate(experiment_service.update_run(db, r, data, user.email, ip))

@router.delete('/{run_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    r = experiment_service.get_run_by_id(db, run_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    ip = request.client.host if request.client else None
    experiment_service.delete_run(db, r, user.email, ip)
