import csv, io, uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_ANALYST, ROLE_VIEWER, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.entities import Artifact, Experiment, Run
from backend.app.models.schemas import ExperimentResponse
from backend.app.services import experiment_service

router = APIRouter(tags=['Import & Export'])

@router.get('/export/runs.csv')
def export_runs_csv(experiment_id: str, variant_name: Optional[str] = None, db: Session = Depends(get_db), user: UserSession = Depends(require_role(ROLE_VIEWER))):
    if not experiment_service.get_experiment_by_id(db, experiment_id):
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    q = db.query(Run).filter(Run.experiment_id == experiment_id)
    if variant_name:
        q = q.filter(Run.variant_name == variant_name)
    runs = q.order_by(Run.created_at.desc()).all()
    mk, hk = sorted({k for r in runs for k in (r.metrics or {})}), sorted({k for r in runs for k in (r.hyperparameters or {})})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=['id', 'name', 'variant_name', 'seed', 'status', 'commit_hash', 'created_at'] + [f'metric_{m}' for m in mk] + [f'hp_{h}' for h in hk])
    w.writeheader()
    for r in runs:
        row = {'id': r.id, 'name': r.name, 'variant_name': r.variant_name, 'seed': r.seed, 'status': r.status, 'commit_hash': r.commit_hash or '', 'created_at': r.created_at.isoformat() if r.created_at else ''}
        row.update({f'metric_{m}': (r.metrics or {}).get(m, '') for m in mk})
        row.update({f'hp_{h}': (r.hyperparameters or {}).get(h, '') for h in hk})
        w.writerow(row)
    fn = f"runs_{experiment_id}_{variant_name}.csv" if variant_name else f"runs_{experiment_id}.csv"
    return Response(content=buf.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{fn}"'})

class ImportBundleRequest(BaseModel):
    bundle: Dict[str, Any]

@router.get('/export/experiments/{experiment_id}')
def export_experiment(experiment_id: str, db: Session = Depends(get_db), user: UserSession = Depends(require_role(ROLE_VIEWER))):
    exp = experiment_service.get_experiment_by_id(db, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    runs_data = [{'name': r.name, 'variant_name': r.variant_name, 'seed': r.seed, 'hyperparameters': r.hyperparameters, 'metrics': r.metrics, 'status': r.status, 'commit_hash': r.commit_hash, 'tags': r.tags, 'notes': r.notes, 'artifacts': [{'name': a.name, 'artifact_type': a.artifact_type, 'file_path': a.file_path, 'file_size_bytes': a.file_size_bytes, 'sha256_hash': a.sha256_hash, 'metadata_json': a.metadata_json} for a in db.query(Artifact).filter(Artifact.run_id == r.id).all()]} for r in db.query(Run).filter(Run.experiment_id == experiment_id).all()]
    return {'version': '1.0', 'format': 'experiment-comparison-hub-bundle', 'experiment': {'name': exp.name, 'description': exp.description, 'domain': exp.domain, 'baseline_variant': exp.baseline_variant}, 'runs': runs_data}

@router.post('/import', status_code=status.HTTP_201_CREATED)
def import_experiment(req: ImportBundleRequest, request: Request, db: Session = Depends(get_db), user: UserSession = Depends(require_role(ROLE_ANALYST))):
    info = req.bundle.get('experiment')
    if not info or 'name' not in info:
        raise HTTPException(status_code=400, detail="Malformed experiment bundle: missing 'experiment.name'")
    exp_id = f'exp_{uuid.uuid4().hex[:12]}'
    exp = Experiment(id=exp_id, name=info['name'], description=info.get('description'), domain=info.get('domain', 'ai-ml'), baseline_variant=info.get('baseline_variant'), created_by=user.email)
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
    ip = request.client.host if request.client else None
    experiment_service.log_audit_event(db, user.email, 'IMPORT_EXPERIMENT', 'experiment', exp_id, {'imported_runs': n_runs, 'imported_artifacts': n_arts}, ip)
    db.commit()
    db.refresh(exp)
    resp = ExperimentResponse.model_validate(exp)
    resp.run_count = n_runs
    return {'status': 'imported', 'experiment': resp, 'runs_imported': n_runs, 'artifacts_imported': n_arts}
