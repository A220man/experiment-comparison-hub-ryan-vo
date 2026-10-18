from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_VIEWER, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.entities import Run
from backend.app.models.schemas import (
    AdvisoryExplanationRequest, AdvisoryExplanationResponse,
    CrossSeedRequest, CrossSeedResponse,
    LeaderboardRequest, LeaderboardResponse, ObjectiveConfig,
    ParetoFrontierResponse, ParetoRequest,
    SensitivityRequest, SensitivityResponse,
)
from backend.app.services import experiment_service
from backend.app.services.llm_service import generate_advisory_explanation
from backend.app.services.leaderboard_engine import compute_variant_leaderboard
from backend.app.services.pareto_engine import aggregate_runs_by_variant, calculate_pareto_frontier
from backend.app.services.sensitivity_engine import analyze_parameter_sensitivity
from backend.app.services.statistics_engine import run_cross_seed_analysis

router = APIRouter(prefix='/analysis', tags=['Analysis'])
_V = Depends(require_role(ROLE_VIEWER))

def _get_exp_runs(db: Session, exp_id: str, vf: Optional[List[str]] = None, sf: Optional[List[int]] = None):
    exp = experiment_service.get_experiment_by_id(db, exp_id)
    if not exp: raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found")
    runs = [{'id': r.id, 'name': r.name, 'variant_name': r.variant_name, 'seed': r.seed, 'hyperparameters': r.hyperparameters or {}, 'metrics': r.metrics or {}} for r in db.query(Run).filter(Run.experiment_id == exp_id).all()]
    if vf: runs = [r for r in runs if r['variant_name'] in vf]
    if sf: runs = [r for r in runs if r['seed'] in sf]
    return exp, runs

@router.post('/pareto', response_model=ParetoFrontierResponse)
def compute_pareto(req: ParetoRequest, db: Session = Depends(get_db), user: UserSession = _V):
    _, runs = _get_exp_runs(db, req.experiment_id, req.variant_filter, req.seed_filter)
    is_agg = req.aggregate_by_variant
    if is_agg:
        runs = aggregate_runs_by_variant(runs, req.objectives, req.aggregation_method)
    return calculate_pareto_frontier(runs, req.objectives, req.experiment_id, is_aggregated=is_agg, aggregation_method=req.aggregation_method if is_agg else None)

@router.post('/cross-seed', response_model=CrossSeedResponse)
def compute_cross_seed(req: CrossSeedRequest, db: Session = Depends(get_db), user: UserSession = _V):
    exp, runs = _get_exp_runs(db, req.experiment_id)
    return run_cross_seed_analysis(runs=runs, baseline_variant=req.baseline_variant or exp.baseline_variant, metrics_to_eval=req.metrics, experiment_id=req.experiment_id, alpha=req.alpha)

@router.post('/sensitivity', response_model=SensitivityResponse)
def compute_sensitivity(req: SensitivityRequest, db: Session = Depends(get_db), user: UserSession = _V):
    _, runs = _get_exp_runs(db, req.experiment_id)
    return analyze_parameter_sensitivity(runs, req.target_metric, req.experiment_id)

@router.post('/advisory-explanation', response_model=AdvisoryExplanationResponse)
async def compute_advisory_explanation(req: AdvisoryExplanationRequest, db: Session = Depends(get_db), user: UserSession = _V):
    exp, runs = _get_exp_runs(db, req.experiment_id)
    m = list(runs[0]['metrics'].keys()) if runs else []
    o1 = 'accuracy' if 'accuracy' in m else (m[0] if m else 'm1')
    o2 = 'latency_ms' if 'latency_ms' in m else (m[1] if len(m) > 1 else 'm2')
    pareto_res = calculate_pareto_frontier(runs, [ObjectiveConfig(metric=o1, direction='maximize'), ObjectiveConfig(metric=o2, direction='minimize')], req.experiment_id)
    eval_m = [k for k in ['accuracy', 'val_loss', 'latency_ms'] if k in m] or m[:3]
    cross_res = run_cross_seed_analysis(runs=runs, baseline_variant=exp.baseline_variant, metrics_to_eval=eval_m, experiment_id=req.experiment_id)
    evidence = {'experiment_name': exp.name, 'baseline_variant': cross_res.baseline_variant, 'total_runs': pareto_res.total_evaluated_runs, 'frontier_count': pareto_res.frontier_runs_count, 'knee_point': pareto_res.knee_point.run_name if pareto_res.knee_point else None, 'hypervolume': pareto_res.hypervolume_indicator, 'comparisons': [c.model_dump() for c in cross_res.hypothesis_tests]}
    return await generate_advisory_explanation(evidence, req.experiment_id)

@router.post('/leaderboard', response_model=LeaderboardResponse)
def compute_leaderboard(req: LeaderboardRequest, db: Session = Depends(get_db), user: UserSession = _V):
    _, runs = _get_exp_runs(db, req.experiment_id, req.variant_filter, req.seed_filter)
    return compute_variant_leaderboard(runs_data=runs, objectives=req.objectives, baseline_variant=req.baseline_variant, experiment_id=req.experiment_id, aggregate_by_variant=req.aggregate_by_variant, aggregation_method=req.aggregation_method, weight_pareto=req.weight_pareto, weight_significance=req.weight_significance)
