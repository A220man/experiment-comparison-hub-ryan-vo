from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_ANALYST, ROLE_VIEWER, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.entities import Artifact
from backend.app.models.schemas import ArtifactCreate, ArtifactResponse, ArtifactVerifyResponse
from backend.app.services import experiment_service
router = APIRouter(tags=['Artifacts'])

@router.get('/runs/{run_id}/artifacts', response_model=List[ArtifactResponse])
def list_artifacts(run_id: str, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    run = experiment_service.get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    artifacts = experiment_service.list_artifacts_for_run(db, run_id)
    return [ArtifactResponse.model_validate(a) for a in artifacts]

@router.post('/runs/{run_id}/artifacts', response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
def register_artifact(run_id: str, data: ArtifactCreate, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    run = experiment_service.get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    data.run_id = run_id
    ip = request.client.host if request.client else None
    artifact = experiment_service.create_artifact(db, data, user.email, ip)
    return ArtifactResponse.model_validate(artifact)

@router.post('/artifacts/{artifact_id}/verify', response_model=ArtifactVerifyResponse)
def verify_artifact(artifact_id: str, request: Request, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_ANALYST))):
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")
    ip = request.client.host if request.client else None
    result = experiment_service.verify_artifact_checksum(db, artifact, user.email, ip)
    return result
