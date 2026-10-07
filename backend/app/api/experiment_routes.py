import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.schemas import ExperimentCreate, ExperimentListResponse, ExperimentResponse, ExperimentUpdate
from backend.app.services import experiment_service

router = APIRouter(prefix='/experiments', tags=['Experiments'])

def _to_resp(exp, count=None) -> ExperimentResponse:
    r = ExperimentResponse.model_validate(exp)
    r.run_count = count if count is not None else (len(exp.runs) if exp.runs else 0)
    return r

@router.get('', response_model=ExperimentListResponse)
def list_experiments(page: int=Query(default=1, ge=1), page_size: int=Query(default=20, ge=1, le=100), search: Optional[str]=None, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    items, total = experiment_service.list_experiments(db, page=page, page_size=page_size, search=search)
    pages = math.ceil(total / page_size) if total > 0 else 1
    return ExperimentListResponse(items=[_to_resp(e) for e in items], total=total, page=page, page_size=page_size, pages=pages)

@router.post('', response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(data: ExperimentCreate, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    ip = request.client.host if request.client else None
    return _to_resp(experiment_service.create_experiment(db, data, user.email, ip), count=0)

@router.get('/{experiment_id}', response_model=ExperimentResponse)
def get_experiment(experiment_id: str, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    exp = experiment_service.get_experiment_by_id(db, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return _to_resp(exp)

@router.put('/{experiment_id}', response_model=ExperimentResponse)
def update_experiment(experiment_id: str, data: ExperimentUpdate, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    exp = experiment_service.get_experiment_by_id(db, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    ip = request.client.host if request.client else None
    return _to_resp(experiment_service.update_experiment(db, exp, data, user.email, ip))

@router.delete('/{experiment_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_experiment(experiment_id: str, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ADMIN))):
    exp = experiment_service.get_experiment_by_id(db, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    ip = request.client.host if request.client else None
    experiment_service.delete_experiment(db, exp, user.email, ip)
