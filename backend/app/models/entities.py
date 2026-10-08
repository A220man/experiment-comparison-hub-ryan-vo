import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

class Experiment(Base):
    __tablename__ = 'experiments'
    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    domain = Column(String(64), default='ai-ml', nullable=False)
    baseline_variant = Column(String(128), nullable=True)
    created_by = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    runs = relationship('Run', back_populates='experiment', cascade='all, delete-orphan')

class Run(Base):
    __tablename__ = 'runs'
    id = Column(String(64), primary_key=True, index=True)
    experiment_id = Column(String(64), ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    variant_name = Column(String(128), nullable=False, index=True)
    seed = Column(Integer, nullable=False, index=True)
    hyperparameters = Column(JSON, default=dict, nullable=False)
    metrics = Column(JSON, default=dict, nullable=False)
    status = Column(String(32), default='COMPLETED', nullable=False)
    commit_hash = Column(String(64), nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    experiment = relationship('Experiment', back_populates='runs')
    artifacts = relationship('Artifact', back_populates='run', cascade='all, delete-orphan')

class Artifact(Base):
    __tablename__ = 'artifacts'
    id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), ForeignKey('runs.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    artifact_type = Column(String(64), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    verified = Column(Boolean, default=True, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    run = relationship('Run', back_populates='artifacts')

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(String(64), primary_key=True, index=True)
    user_email = Column(String(128), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(String(64), nullable=False)
    details_json = Column(JSON, default=dict, nullable=False)
    ip_address = Column(String(64), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
