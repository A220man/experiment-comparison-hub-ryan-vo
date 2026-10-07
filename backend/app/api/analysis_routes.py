from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_VIEWER, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.entities import Run
from backend.app.models.schemas import AdvisoryExplanationRequest, AdvisoryExplanationResponse, CrossSeedRequest, CrossSeedResponse, ObjectiveConfig, ParetoFrontierResponse, ParetoRequest, SensitivityRequest, SensitivityResponse
from backend.app.services import experiment_service
from backend.app.services.llm_service import generate_advisory_explanation
from backend.app.services.pareto_engine import calculate_pareto_frontier
from backend.app.services.sensitivity_engine import analyze_parameter_sensitivity
from backend.app.services.statistics_engine import run_cross_seed_analysis

router = APIRouter(prefix='/analysis', tags=['Analysis'])

def _get_experiment_runs_dicts(db: Session, experiment_id: str) -> List[dict]:
    runs = db.query(Run).filter(Run.experiment_id == experiment_id).all()
    return [{'id': r.id, 'name': r.name, 'variant_name': r.variant_name, 'seed': r.seed, 'hyperparameters': r.hyperparameters or {}, 'metrics': r.metrics or {}} for r in runs]

def _get_valid_experiment(db: Session, exp_id: str):
    exp = experiment_service.get_experiment_by_id(db, exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found")
    return exp

@router.post('/pareto', response_model=ParetoFrontierResponse)
def compute_pareto(req: ParetoRequest, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    _get_valid_experiment(db, req.experiment_id)
    runs = _get_experiment_runs_dicts(db, req.experiment_id)
    if req.variant_filter:
        runs = [r for r in runs if r['variant_name'] in req.variant_filter]
    return calculate_pareto_frontier(runs, req.objectives, req.experiment_id)

@router.post('/cross-seed', response_model=CrossSeedResponse)
def compute_cross_seed(req: CrossSeedRequest, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    exp = _get_valid_experiment(db, req.experiment_id)
    runs = _get_experiment_runs_dicts(db, req.experiment_id)
    return run_cross_seed_analysis(runs=runs, baseline_variant=req.baseline_variant or exp.baseline_variant, metrics_to_eval=req.metrics, experiment_id=req.experiment_id, alpha=req.alpha)

@router.post('/sensitivity', response_model=SensitivityResponse)
def compute_sensitivity(req: SensitivityRequest, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    _get_valid_experiment(db, req.experiment_id)
    return analyze_parameter_sensitivity(_get_experiment_runs_dicts(db, req.experiment_id), req.target_metric, req.experiment_id)

@router.post('/advisory-explanation', response_model=AdvisoryExplanationResponse)
async def compute_advisory_explanation(req: AdvisoryExplanationRequest, db: Session=Depends(get_db), user: UserSession=Depends(require_role(ROLE_VIEWER))):
    exp = _get_valid_experiment(db, req.experiment_id)
    runs = _get_experiment_runs_dicts(db, req.experiment_id)
    metrics = list(runs[0]['metrics'].keys()) if runs else []
    o1 = 'accuracy' if 'accuracy' in metrics else (metrics[0] if metrics else 'm1')
    o2 = 'latency_ms' if 'latency_ms' in metrics else (metrics[1] if len(metrics) > 1 else 'm2')
    pareto_res = calculate_pareto_frontier(runs, [ObjectiveConfig(metric=o1, direction='maximize'), ObjectiveConfig(metric=o2, direction='minimize')], req.experiment_id)
    eval_m = [m for m in ['accuracy', 'val_loss', 'latency_ms'] if m in metrics] or metrics[:3]
    cross_res = run_cross_seed_analysis(runs=runs, baseline_variant=exp.baseline_variant, metrics_to_eval=eval_m, experiment_id=req.experiment_id)
    evidence = {
        'experiment_name': exp.name,
        'baseline_variant': cross_res.baseline_variant,
        'total_runs': pareto_res.total_evaluated_runs,
        'frontier_count': pareto_res.frontier_runs_count,
        'knee_point': pareto_res.knee_point.run_name if pareto_res.knee_point else None,
        'hypervolume': pareto_res.hypervolume_indicator,
        'comparisons': [{'treatment_variant': c.treatment_variant, 'baseline_variant': c.baseline_variant, 'metric': c.metric, 'mean_delta': c.mean_delta, 'percent_change': c.percent_change, 'p_value_welch': c.p_value_welch, 'cohens_d': c.cohens_d, 'is_statistically_significant': c.is_statistically_significant, 'significance_label': c.significance_label} for c in cross_res.hypothesis_tests]
    }
    return await generate_advisory_explanation(evidence, req.experiment_id)
