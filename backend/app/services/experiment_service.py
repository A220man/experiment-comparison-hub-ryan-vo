import math
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from backend.app.core.security import calculate_file_sha256
from backend.app.models.entities import Artifact, AuditLog, Experiment, Run
from backend.app.models.schemas import ArtifactCreate, ArtifactVerifyResponse, ExperimentCreate, ExperimentUpdate, MetricDelta, ParameterDelta, RunCreate, RunDiffResponse, RunResponse, RunUpdate

def log_audit_event(db: Session, user_email: str, action: str, resource_type: str, resource_id: str, details: Dict[str, Any], ip_address: Optional[str]=None) -> AuditLog:
    log = AuditLog(id=f'aud_{uuid.uuid4().hex[:12]}', user_email=user_email, action=action, resource_type=resource_type, resource_id=resource_id, details_json=details, ip_address=ip_address)
    db.add(log)
    db.flush()
    return log

def create_experiment(db: Session, data: ExperimentCreate, user_email: str, ip_address: Optional[str]=None) -> Experiment:
    exp = Experiment(id=f'exp_{uuid.uuid4().hex[:12]}', name=data.name, description=data.description, domain=data.domain, baseline_variant=data.baseline_variant, created_by=user_email)
    db.add(exp)
    log_audit_event(db, user_email, 'CREATE_EXPERIMENT', 'experiment', exp.id, {'name': exp.name}, ip_address)
    db.commit()
    db.refresh(exp)
    return exp

def get_experiment_by_id(db: Session, experiment_id: str) -> Optional[Experiment]:
    return db.query(Experiment).filter(Experiment.id == experiment_id).first()

def list_experiments(db: Session, page: int=1, page_size: int=20, search: Optional[str]=None) -> Tuple[List[Experiment], int]:
    query = db.query(Experiment)
    if search:
        query = query.filter(Experiment.name.ilike(f'%{search}%'))
    total = query.count()
    items = query.order_by(desc(Experiment.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return (items, total)

def update_experiment(db: Session, experiment: Experiment, data: ExperimentUpdate, user_email: str, ip_address: Optional[str]=None) -> Experiment:
    changes = {}
    for f in ('name', 'description', 'baseline_variant'):
        v = getattr(data, f)
        if v is not None:
            changes[f] = (getattr(experiment, f), v)
            setattr(experiment, f, v)
    if changes:
        log_audit_event(db, user_email, 'UPDATE_EXPERIMENT', 'experiment', experiment.id, changes, ip_address)
        db.commit()
        db.refresh(experiment)
    return experiment

def delete_experiment(db: Session, experiment: Experiment, user_email: str, ip_address: Optional[str]=None) -> None:
    exp_id = experiment.id
    db.delete(experiment)
    log_audit_event(db, user_email, 'DELETE_EXPERIMENT', 'experiment', exp_id, {'deleted_id': exp_id}, ip_address)
    db.commit()

def create_run(db: Session, data: RunCreate, user_email: str, ip_address: Optional[str]=None) -> Run:
    run = Run(id=f'run_{uuid.uuid4().hex[:12]}', experiment_id=data.experiment_id, name=data.name, variant_name=data.variant_name, seed=data.seed, hyperparameters=data.hyperparameters, metrics=data.metrics, status=data.status, commit_hash=data.commit_hash, tags=data.tags, notes=data.notes, created_by=user_email)
    db.add(run)
    log_audit_event(db, user_email, 'CREATE_RUN', 'run', run.id, {'experiment_id': run.experiment_id, 'variant': run.variant_name, 'seed': run.seed}, ip_address)
    db.commit()
    db.refresh(run)
    return run

def get_run_by_id(db: Session, run_id: str) -> Optional[Run]:
    return db.query(Run).filter(Run.id == run_id).first()

def list_runs(db: Session, experiment_id: str, page: int=1, page_size: int=50, variant_name: Optional[str]=None, seed: Optional[int]=None, tag: Optional[str]=None) -> Tuple[List[Run], int]:
    query = db.query(Run).filter(Run.experiment_id == experiment_id)
    if variant_name:
        query = query.filter(Run.variant_name == variant_name)
    if seed is not None:
        query = query.filter(Run.seed == seed)
    total = query.count()
    items = query.order_by(desc(Run.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    if tag:
        items = [r for r in items if tag in (r.tags or [])]
    return (items, total)

def update_run(db: Session, run: Run, data: RunUpdate, user_email: str, ip_address: Optional[str]=None) -> Run:
    changes = {}
    for f in ('name', 'notes', 'status', 'tags'):
        v = getattr(data, f)
        if v is not None:
            changes[f] = v
            setattr(run, f, v)
    if data.metrics is not None:
        changes['metrics'] = data.metrics
        run.metrics = {**run.metrics, **data.metrics}
    if changes:
        log_audit_event(db, user_email, 'UPDATE_RUN', 'run', run.id, changes, ip_address)
        db.commit()
        db.refresh(run)
    return run

def delete_run(db: Session, run: Run, user_email: str, ip_address: Optional[str]=None) -> None:
    run_id = run.id
    db.delete(run)
    log_audit_event(db, user_email, 'DELETE_RUN', 'run', run_id, {'deleted_id': run_id}, ip_address)
    db.commit()

def diff_runs(base_run: Run, target_run: Run) -> RunDiffResponse:
    bp, tp = base_run.hyperparameters or {}, target_run.hyperparameters or {}
    all_keys = sorted(set(bp.keys()) | set(tp.keys()))
    param_deltas = [ParameterDelta(parameter=k, base_value=bp.get(k), target_value=tp.get(k), changed=bp.get(k) != tp.get(k)) for k in all_keys]
    bm, tm = base_run.metrics or {}, target_run.metrics or {}
    lower_is_better = {'loss', 'val_loss', 'latency_ms', 'perplexity', 'error_rate', 'memory_mb', 'flpop'}
    metric_deltas = []
    for m in sorted(set(bm.keys()) | set(tm.keys())):
        bv, tv = bm.get(m), tm.get(m)
        abs_d = round(float(tv) - float(bv), 5) if bv is not None and tv is not None else None
        pct_d = round(abs_d / abs(bv) * 100.0 if bv != 0 else 0.0, 3) if abs_d is not None and bv is not None else None
        imp = (abs_d < 0 if m.lower() in lower_is_better else abs_d > 0) if abs_d is not None else None
        metric_deltas.append(MetricDelta(metric=m, base_value=bv, target_value=tv, absolute_delta=abs_d, percent_change=pct_d, improved=imp))
    return RunDiffResponse(base_run=RunResponse.model_validate(base_run), target_run=RunResponse.model_validate(target_run), parameter_deltas=param_deltas, metric_deltas=metric_deltas)

def create_artifact(db: Session, data: ArtifactCreate, user_email: str, ip_address: Optional[str]=None) -> Artifact:
    art = Artifact(id=f'art_{uuid.uuid4().hex[:12]}', run_id=data.run_id, name=data.name, artifact_type=data.artifact_type, file_path=data.file_path, file_size_bytes=data.file_size_bytes, sha256_hash=data.sha256_hash, verified=True, metadata_json=data.metadata_json)
    db.add(art)
    log_audit_event(db, user_email, 'REGISTER_ARTIFACT', 'artifact', art.id, {'run_id': art.run_id, 'name': art.name, 'sha256': art.sha256_hash}, ip_address)
    db.commit()
    db.refresh(art)
    return art

def list_artifacts_for_run(db: Session, run_id: str) -> List[Artifact]:
    return db.query(Artifact).filter(Artifact.run_id == run_id).order_by(desc(Artifact.created_at)).all()

def verify_artifact_checksum(db: Session, artifact: Artifact, user_email: str, ip_address: Optional[str]=None) -> ArtifactVerifyResponse:
    actual = calculate_file_sha256(artifact.file_path)
    ok = actual is not None and actual.lower() == artifact.sha256_hash.lower()
    msg = f"Artifact file '{artifact.file_path}' does not exist on disk." if actual is None else ('SHA-256 cryptographic checksum verified successfully.' if ok else f'CHECKSUM MISMATCH: expected {artifact.sha256_hash}, computed {actual}.')
    artifact.verified = ok
    log_audit_event(db, user_email, 'VERIFY_ARTIFACT', 'artifact', artifact.id, {'verified': ok, 'message': msg}, ip_address)
    db.commit()
    return ArtifactVerifyResponse(artifact_id=artifact.id, name=artifact.name, expected_sha256=artifact.sha256_hash, actual_sha256=actual, verified=ok, message=msg)
