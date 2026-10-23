from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.auth import ROLE_VIEWER, UserSession, require_role
from backend.app.core.database import get_db
from backend.app.models.entities import Run
from backend.app.models.schemas import (
    ObjectiveConfig,
    ParetoRequest,
    SensitivityRequest,
    TuningRecommendationsResponse,
)
from backend.app.services import experiment_service
from backend.app.services.pareto_engine import calculate_pareto_frontier
from backend.app.services.sensitivity_engine import analyze_parameter_sensitivity
from backend.app.services.tuning_engine import generate_tuning_recommendations

router = APIRouter(prefix='/tuning', tags=['Hyperparameter Tuning'])
_V = Depends(require_role(ROLE_VIEWER))


def _get_exp_runs(db: Session, exp_id: str):
    exp = experiment_service.get_experiment_by_id(db, exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found")
    runs = [{'id': r.id, 'name': r.name, 'variant_name': r.variant_name, 'seed': r.seed,
             'hyperparameters': r.hyperparameters or {}, 'metrics': r.metrics or {}}
            for r in db.query(Run).filter(Run.experiment_id == exp_id).all()]
    return exp, runs


@router.post('/recommendations', response_model=TuningRecommendationsResponse)
def get_tuning_recommendations(
    experiment_id: str,
    target_metric: str = "accuracy",
    objectives: Optional[List[ObjectiveConfig]] = None,
    variant_filter: Optional[List[str]] = None,
    seed_filter: Optional[List[int]] = None,
    aggregate_by_variant: bool = False,
    aggregation_method: str = "mean",
    db: Session = Depends(get_db),
    user: UserSession = _V,
):
    """Generate automated hyperparameter tuning recommendations.

    Combines sensitivity analysis (Spearman/Pearson correlation, ANOVA) with
    Pareto knee point configurations to provide search interval recommendations
    and boundary suggestions for influential hyperparameters.

    Args:
        experiment_id: Experiment to analyze
        target_metric: Primary metric for sensitivity analysis (default: accuracy)
        objectives: Optional Pareto objectives for knee point recommendations
        variant_filter: Optional variant names to include
        seed_filter: Optional seed values to include
        aggregate_by_variant: Whether to aggregate multi-seed runs by variant
        aggregation_method: 'mean' or 'median' for variant aggregation
    """
    exp, runs = _get_exp_runs(db, experiment_id)

    if variant_filter:
        runs = [r for r in runs if r['variant_name'] in variant_filter]
    if seed_filter:
        runs = [r for r in runs if r['seed'] in seed_filter]

    if not runs:
        raise HTTPException(status_code=400, detail="No runs found for the given filters")

    # Run sensitivity analysis
    sensitivity = analyze_parameter_sensitivity(runs, target_metric, experiment_id)

    # Run Pareto analysis if objectives provided (for knee point recommendations)
    pareto_response = None
    if objectives and len(objectives) >= 2:
        pareto_req = ParetoRequest(
            experiment_id=experiment_id,
            objectives=objectives,
            variant_filter=variant_filter,
            seed_filter=seed_filter,
            aggregate_by_variant=aggregate_by_variant,
            aggregation_method=aggregation_method,
        )
        pareto_response = calculate_pareto_frontier(
            runs=pareto_req.objectives and runs or [],  # runs already filtered above
            objectives=objectives,
            experiment_id=experiment_id,
            is_aggregated=aggregate_by_variant,
            aggregation_method=aggregation_method if aggregate_by_variant else None,
        )

    # Generate combined recommendations
    result = generate_tuning_recommendations(
        runs=runs,
        sensitivity_response=sensitivity,
        pareto_response=pareto_response,
        objectives=objectives,
    )

    return result