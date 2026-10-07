import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_ANALYST, ROLE_VIEWER, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.entities import Artifact, Experiment, Run
from backend.app.models.schemas import ExperimentResponse
from backend.app.services import experiment_service

router = APIRouter(tags=['Import & Export'])

class ImportBundleRequest(BaseModel):
    bundle: Dict[str, Any]

@router.get('/export/experiments/{experiment_id}')
def export_experiment(experiment_id: str, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    exp = experiment_service.get_experiment_by_id(db, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    runs_data = []
    for r in db.query(Run).filter(Run.experiment_id == experiment_id).all():
        arts = db.query(Artifact).filter(Artifact.run_id == r.id).all()
        runs_data.append({'name': r.name, 'variant_name': r.variant_name, 'seed': r.seed, 'hyperparameters': r.hyperparameters, 'metrics': r.metrics, 'status': r.status, 'commit_hash': r.commit_hash, 'tags': r.tags, 'notes': r.notes, 'artifacts': [{'name': a.name, 'artifact_type': a.artifact_type, 'file_path': a.file_path, 'file_size_bytes': a.file_size_bytes, 'sha256_hash': a.sha256_hash, 'metadata_json': a.metadata_json} for a in arts]})
    return {'version': '1.0', 'format': 'experiment-comparison-hub-bundle', 'experiment': {'name': exp.name, 'description': exp.description, 'domain': exp.domain, 'baseline_variant': exp.baseline_variant}, 'runs': runs_data}

@router.post('/import', status_code=status.HTTP_201_CREATED)
def import_experiment(req: ImportBundleRequest, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    exp_info = req.bundle.get('experiment')
    if not exp_info or 'name' not in exp_info:
        raise HTTPException(status_code=400, detail="Malformed experiment bundle: missing 'experiment.name'")
    ip = request.client.host if request.client else None
    exp_id = f'exp_{uuid.uuid4().hex[:12]}'
    exp = Experiment(id=exp_id, name=exp_info['name'], description=exp_info.get('description'), domain=exp_info.get('domain', 'ai-ml'), baseline_variant=exp_info.get('baseline_variant'), created_by=user.email)
    db.add(exp)
    n_runs, n_arts = 0, 0
    for r in req.bundle.get('runs', []):
        rid = f'run_{uuid.uuid4().hex[:12]}'
        db.add(Run(id=rid, experiment_id=exp_id, name=r.get('name', 'Run'), variant_name=r.get('variant_name', 'default'), seed=int(r.get('seed', 42)), hyperparameters=r.get('hyperparameters', {}), metrics=r.get('metrics', {}), status=r.get('status', 'COMPLETED'), commit_hash=r.get('commit_hash'), tags=r.get('tags', []), notes=r.get('notes'), created_by=user.email))
        n_runs += 1
        for a in r.get('artifacts', []):
            aid = f'art_{uuid.uuid4().hex[:12]}'
            db.add(Artifact(id=aid, run_id=rid, name=a.get('name', 'Artifact'), artifact_type=a.get('artifact_type', 'checkpoint'), file_path=a.get('file_path', f'/storage/{aid}.bin'), file_size_bytes=int(a.get('file_size_bytes', 0)), sha256_hash=a.get('sha256_hash', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), verified=True, metadata_json=a.get('metadata_json', {})))
            n_arts += 1
    experiment_service.log_audit_event(db, user.email, 'IMPORT_EXPERIMENT', 'experiment', exp_id, {'imported_runs': n_runs, 'imported_artifacts': n_arts}, ip)
    db.commit()
    db.refresh(exp)
    resp = ExperimentResponse.model_validate(exp)
    resp.run_count = n_runs
    return {'status': 'imported', 'experiment': resp, 'runs_imported': n_runs, 'artifacts_imported': n_arts}
