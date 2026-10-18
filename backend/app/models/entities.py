import datetime
from sqlalchemy import Boolean, Column as C, DateTime as DT, ForeignKey as FK, Integer as I, JSON as J, String as S, Text as T
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

utc_now = lambda: datetime.datetime.now(datetime.timezone.utc)
pk = lambda: C(S(64), primary_key=True, index=True)
dt_now = lambda **kw: C(DT(timezone=True), default=utc_now, nullable=False, **kw)
s128 = lambda **kw: C(S(128), nullable=False, **kw)
js_dict = lambda: C(J, default=dict, nullable=False)

class Experiment(Base):
    __tablename__ = 'experiments'
    id = pk()
    name = C(S(255), nullable=False, index=True)
    description = C(T, nullable=True)
    domain = C(S(64), default='ai-ml', nullable=False)
    baseline_variant = C(S(128), nullable=True)
    created_by = s128()
    created_at = dt_now()
    updated_at = dt_now(onupdate=utc_now)
    runs = relationship('Run', back_populates='experiment', cascade='all, delete-orphan')

class Run(Base):
    __tablename__ = 'runs'
    id = pk()
    experiment_id = C(S(64), FK('experiments.id', ondelete='CASCADE'), nullable=False, index=True)
    name = C(S(255), nullable=False)
    variant_name = s128(index=True)
    seed = C(I, nullable=False, index=True)
    hyperparameters = js_dict()
    metrics = js_dict()
    status = C(S(32), default='COMPLETED', nullable=False)
    commit_hash = C(S(64), nullable=True)
    tags = C(J, default=list, nullable=False)
    notes = C(T, nullable=True)
    created_by = s128()
    created_at = dt_now()
    experiment = relationship('Experiment', back_populates='runs')
    artifacts = relationship('Artifact', back_populates='run', cascade='all, delete-orphan')

class Artifact(Base):
    __tablename__ = 'artifacts'
    id = pk()
    run_id = C(S(64), FK('runs.id', ondelete='CASCADE'), nullable=False, index=True)
    name = C(S(255), nullable=False)
    artifact_type = C(S(64), nullable=False)
    file_path = C(S(512), nullable=False)
    file_size_bytes = C(I, default=0, nullable=False)
    sha256_hash = C(S(64), nullable=False)
    verified = C(Boolean, default=True, nullable=False)
    metadata_json = js_dict()
    created_at = dt_now()
    run = relationship('Run', back_populates='artifacts')

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = pk()
    user_email = s128(index=True)
    action = C(S(64), nullable=False, index=True)
    resource_type = C(S(64), nullable=False, index=True)
    resource_id = C(S(64), nullable=False)
    details_json = js_dict()
    ip_address = C(S(64), nullable=True)
    timestamp = dt_now(index=True)
