import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc
from sqlalchemy.orm import Session
from backend.app.core.security import calculate_file_sha256
from backend.app.models.entities import Artifact, AuditLog, Experiment, Run
from backend.app.models.schemas import (
    ArtifactCreate, ArtifactVerifyResponse, ExperimentCreate, ExperimentUpdate,
    MetricDelta, ParameterDelta, RunCreate, RunDiffResponse, RunResponse, RunUpdate,
)

def log_audit_event(db: Session, email: str, action: str, res_type: str, res_id: str, details: Dict[str, Any], ip: Optional[str] = None) -> AuditLog:
    log = AuditLog(id=f'aud_{uuid.uuid4().hex[:12]}', user_email=email, action=action, resource_type=res_type, resource_id=res_id, details_json=details, ip_address=ip)
    db.add(log)
    db.flush()
    return log

def create_experiment(db: Session, data: ExperimentCreate, email: str, ip: Optional[str] = None) -> Experiment:
    exp = Experiment(id=f'exp_{uuid.uuid4().hex[:12]}', name=data.name, description=data.description, domain=data.domain, baseline_variant=data.baseline_variant, created_by=email)
    db.add(exp)
    log_audit_event(db, email, 'CREATE_EXPERIMENT', 'experiment', exp.id, {'name': exp.name}, ip)
    db.commit()
    db.refresh(exp)
    return exp

def get_experiment_by_id(db: Session, exp_id: str) -> Optional[Experiment]:
    return db.query(Experiment).filter(Experiment.id == exp_id).first()

def list_experiments(db: Session, page: int = 1, page_size: int = 20, search: Optional[str] = None) -> Tuple[List[Experiment], int]:
    q = db.query(Experiment)
    if search: q = q.filter(Experiment.name.ilike(f'%{search}%'))
    return (q.order_by(desc(Experiment.created_at)).offset((page - 1) * page_size).limit(page_size).all(), q.count())

def update_experiment(db: Session, exp: Experiment, data: ExperimentUpdate, email: str, ip: Optional[str] = None) -> Experiment:
    ch = {f: (getattr(exp, f), getattr(data, f)) for f in ('name', 'description', 'baseline_variant') if getattr(data, f) is not None}
    for f, (_, v) in ch.items(): setattr(exp, f, v)
    if ch:
        log_audit_event(db, email, 'UPDATE_EXPERIMENT', 'experiment', exp.id, ch, ip)
        db.commit()
        db.refresh(exp)
    return exp

def delete_experiment(db: Session, exp: Experiment, email: str, ip: Optional[str] = None) -> None:
    exp_id = exp.id
    db.delete(exp)
    log_audit_event(db, email, 'DELETE_EXPERIMENT', 'experiment', exp_id, {'deleted_id': exp_id}, ip)
    db.commit()

def create_run(db: Session, data: RunCreate, email: str, ip: Optional[str] = None) -> Run:
    run = Run(id=f'run_{uuid.uuid4().hex[:12]}', experiment_id=data.experiment_id, name=data.name, variant_name=data.variant_name, seed=data.seed, hyperparameters=data.hyperparameters, metrics=data.metrics, status=data.status, commit_hash=data.commit_hash, tags=data.tags, notes=data.notes, created_by=email)
    db.add(run)
    log_audit_event(db, email, 'CREATE_RUN', 'run', run.id, {'experiment_id': run.experiment_id, 'variant': run.variant_name, 'seed': run.seed}, ip)
    db.commit()
    db.refresh(run)
    return run

def get_run_by_id(db: Session, run_id: str) -> Optional[Run]:
    return db.query(Run).filter(Run.id == run_id).first()

def list_runs(db: Session, experiment_id: str, page: int = 1, page_size: int = 50, variant_name: Optional[str] = None, seed: Optional[int] = None, tag: Optional[str] = None) -> Tuple[List[Run], int]:
    q = db.query(Run).filter(Run.experiment_id == experiment_id)
    if variant_name: q = q.filter(Run.variant_name == variant_name)
    if seed is not None: q = q.filter(Run.seed == seed)
    tot = q.count()
    items = q.order_by(desc(Run.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    if tag: items = [r for r in items if tag in (r.tags or [])]
    return (items, tot)


def update_run(db: Session, run: Run, data: RunUpdate, email: str, ip: Optional[str] = None) -> Run:
    ch = {f: getattr(data, f) for f in ('name', 'notes', 'status', 'tags') if getattr(data, f) is not None}
    for f, v in ch.items(): setattr(run, f, v)
    if data.metrics is not None:
        ch['metrics'] = data.metrics
        run.metrics = {**run.metrics, **data.metrics}
    if ch:
        log_audit_event(db, email, 'UPDATE_RUN', 'run', run.id, ch, ip)
        db.commit()
        db.refresh(run)
    return run

def delete_run(db: Session, run: Run, email: str, ip: Optional[str] = None) -> None:
    rid = run.id
    db.delete(run)
    log_audit_event(db, email, 'DELETE_RUN', 'run', rid, {'deleted_id': rid}, ip)
    db.commit()

def is_lower_better(m: str) -> bool:
    s = m.lower()
    return any(x in s for x in ('loss', 'latency', 'error', 'perplexity', 'memory', 'cost', 'flop'))

def diff_runs(base_run: Run, target_run: Run) -> RunDiffResponse:
    bp, tp = base_run.hyperparameters or {}, target_run.hyperparameters or {}
    p_deltas = [ParameterDelta(parameter=k, base_value=bp.get(k), target_value=tp.get(k), changed=bp.get(k) != tp.get(k)) for k in sorted(set(bp) | set(tp))]
    bm, tm = base_run.metrics or {}, target_run.metrics or {}
    m_deltas = []
    for m in sorted(set(bm) | set(tm)):
        bv, tv = bm.get(m), tm.get(m)
        d = round(float(tv) - float(bv), 5) if bv is not None and tv is not None else None
        pct = round(d / abs(bv) * 100.0, 3) if d is not None and bv not in (0, None) else 0.0 if d == 0 else None
        imp = (d < 0 if is_lower_better(m) else d > 0) if d is not None else None
        m_deltas.append(MetricDelta(metric=m, base_value=bv, target_value=tv, absolute_delta=d, percent_change=pct, improved=imp))
    return RunDiffResponse(base_run=RunResponse.model_validate(base_run), target_run=RunResponse.model_validate(target_run), parameter_deltas=p_deltas, metric_deltas=m_deltas)

def create_artifact(db: Session, data: ArtifactCreate, email: str, ip: Optional[str] = None) -> Artifact:
    art = Artifact(id=f'art_{uuid.uuid4().hex[:12]}', run_id=data.run_id, name=data.name, artifact_type=data.artifact_type, file_path=data.file_path, file_size_bytes=data.file_size_bytes, sha256_hash=data.sha256_hash, verified=True, metadata_json=data.metadata_json)
    db.add(art)
    log_audit_event(db, email, 'REGISTER_ARTIFACT', 'artifact', art.id, {'run_id': art.run_id, 'name': art.name, 'sha256': art.sha256_hash}, ip)
    db.commit()
    db.refresh(art)
    return art

def list_artifacts_for_run(db: Session, run_id: str) -> List[Artifact]:
    return db.query(Artifact).filter(Artifact.run_id == run_id).order_by(desc(Artifact.created_at)).all()

def verify_artifact_checksum(db: Session, art: Artifact, email: str, ip: Optional[str] = None) -> ArtifactVerifyResponse:
    actual = calculate_file_sha256(art.file_path)
    ok = actual is not None and actual.lower() == art.sha256_hash.lower()
    msg = f"Artifact file '{art.file_path}' does not exist on disk." if actual is None else ('SHA-256 cryptographic checksum verified successfully.' if ok else f'CHECKSUM MISMATCH: expected {art.sha256_hash}, computed {actual}.')
    art.verified = ok
    log_audit_event(db, email, 'VERIFY_ARTIFACT', 'artifact', art.id, {'verified': ok, 'message': msg}, ip)
    db.commit()
    return ArtifactVerifyResponse(artifact_id=art.id, name=art.name, expected_sha256=art.sha256_hash, actual_sha256=actual, verified=ok, message=msg)
