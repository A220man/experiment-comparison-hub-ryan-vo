"""Automated Hyperparameter Tuning Recommendations Engine.

Builds on sensitivity analysis and Pareto optimization to provide actionable
search interval recommendations and boundary suggestions for hyperparameter tuning.
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

from backend.app.models.schemas import (
    ObjectiveConfig,
    ParameterSensitivity,
    ParetoPoint,
    SensitivityResponse,
    ParetoFrontierResponse,
)


class TuningRecommendation:
    """Recommendation for a single hyperparameter."""

    def __init__(
        self,
        parameter: str,
        parameter_type: str,
        current_range: Tuple[float, float] | List[str],
        recommended_range: Tuple[float, float] | List[str],
        rationale: str,
        confidence: float,
        priority: str,
        source: str,
    ):
        self.parameter = parameter
        self.parameter_type = parameter_type
        self.current_range = current_range
        self.recommended_range = recommended_range
        self.rationale = rationale
        self.confidence = confidence
        self.priority = priority  # 'high', 'medium', 'low'
        self.source = source  # 'sensitivity', 'pareto_knee', 'combined'

    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "parameter_type": self.parameter_type,
            "current_range": list(self.current_range) if isinstance(self.current_range, tuple) else self.current_range,
            "recommended_range": list(self.recommended_range) if isinstance(self.recommended_range, tuple) else self.recommended_range,
            "rationale": self.rationale,
            "confidence": round(self.confidence, 3),
            "priority": self.priority,
            "source": self.source,
        }


class TuningRecommendationsResponse:
    """Container for all tuning recommendations."""

    def __init__(
        self,
        experiment_id: str,
        target_metric: str,
        recommendations: List[TuningRecommendation],
        sensitivity_summary: Dict,
        pareto_knee_config: Optional[Dict] = None,
    ):
        self.experiment_id = experiment_id
        self.target_metric = target_metric
        self.recommendations = recommendations
        self.sensitivity_summary = sensitivity_summary
        self.pareto_knee_config = pareto_knee_config

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "target_metric": self.target_metric,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "sensitivity_summary": self.sensitivity_summary,
            "pareto_knee_config": self.pareto_knee_config,
        }


def _get_observed_range(runs: List[dict], param: str) -> Tuple[float, float] | List[str]:
    """Extract observed min/max for numeric or unique values for categorical."""
    values = []
    for r in runs:
        val = r.get('hyperparameters', {}).get(param)
        if val is not None:
            values.append(val)
    if not values:
        return (0.0, 0.0)
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return (min(values), max(values))
    return sorted(set(str(v) for v in values))


def _get_knee_point_hyperparameters(
    runs: List[dict],
    knee_point: Optional[ParetoPoint],
) -> Optional[Dict[str, float | str]]:
    """Extract hyperparameter configuration from the knee point run."""
    if not knee_point:
        return None
    # Find the original run matching the knee point
    for r in runs:
        if r['id'] == knee_point.run_id:
            return r.get('hyperparameters', {})
    return None


def _recommend_numeric_range_from_sensitivity(
    param: str,
    sensitivity: ParameterSensitivity,
    observed_range: Tuple[float, float],
    target_metric: str,
    direction: str,
) -> Optional[TuningRecommendation]:
    """Generate range recommendation based on sensitivity correlation."""
    rho = sensitivity.spearman_rho or 0.0
    importance = sensitivity.importance_score
    curr_min, curr_max = observed_range

    if importance < 0.1:
        # Negligible correlation - don't recommend changes
        return None

    # Calculate range expansion/contraction based on correlation strength
    range_span = curr_max - curr_min
    if range_span == 0:
        return None

    # For strong positive correlation: explore higher values
    # For strong negative correlation: explore lower values
    # For moderate: expand range to find optimum
    expansion_factor = max(0.2, min(0.5, importance))

    if rho > 0.3:
        # Positive correlation: push upper bound
        new_min = curr_min
        new_max = curr_max + range_span * expansion_factor
        rationale = f"Strong positive Spearman correlation (ρ={rho:.3f}) with {target_metric}. Increasing {param} tends to improve performance."
        priority = "high" if importance > 0.5 else "medium"
    elif rho < -0.3:
        # Negative correlation: push lower bound
        new_min = max(0, curr_min - range_span * expansion_factor) if curr_min >= 0 else curr_min - range_span * expansion_factor
        new_max = curr_max
        rationale = f"Strong negative Spearman correlation (ρ={rho:.3f}) with {target_metric}. Decreasing {param} tends to improve performance."
        priority = "high" if importance > 0.5 else "medium"
    else:
        # Weak/negligible: expand both directions to search for optimum
        new_min = curr_min - range_span * expansion_factor
        new_max = curr_max + range_span * expansion_factor
        rationale = f"Moderate correlation (ρ={rho:.3f}) with {target_metric}. Optimum may lie outside observed range; expanding search bounds."
        priority = "medium"

    confidence = min(0.9, 0.4 + importance * 0.5)

    return TuningRecommendation(
        parameter=param,
        parameter_type='numeric',
        current_range=observed_range,
        recommended_range=(round(new_min, 4), round(new_max, 4)),
        rationale=rationale,
        confidence=confidence,
        priority=priority,
        source='sensitivity',
    )


def _recommend_categorical_from_sensitivity(
    param: str,
    sensitivity: ParameterSensitivity,
    observed_values: List[str],
    runs: List[dict],
    target_metric: str,
) -> Optional[TuningRecommendation]:
    """Generate recommendation for categorical parameter based on ANOVA."""
    if sensitivity.importance_score < 0.1:
        return None

    # Find best performing category
    groups: Dict[str, List[float]] = {}
    for r in runs:
        val = str(r.get('hyperparameters', {}).get(param, ''))
        metric_val = r.get('metrics', {}).get(target_metric)
        if metric_val is not None:
            groups.setdefault(val, []).append(float(metric_val))

    if not groups:
        return None

    best_cat = max(groups.keys(), key=lambda k: np.mean(groups[k]))
    best_mean = np.mean(groups[best_cat])

    # Find worst for comparison
    worst_cat = min(groups.keys(), key=lambda k: np.mean(groups[k]))
    worst_mean = np.mean(groups[worst_cat])

    rationale = f"ANOVA indicates categorical parameter '{param}' significantly affects {target_metric} (F-statistic implied importance={sensitivity.importance_score:.3f}). Best observed category: '{best_cat}' (mean={best_mean:.4f}) vs worst: '{worst_cat}' (mean={worst_mean:.4f}). Consider focusing search on top-performing categories."

    # Recommend keeping top 2 categories if more than 2 exist
    if len(groups) > 2:
        sorted_cats = sorted(groups.keys(), key=lambda k: np.mean(groups[k]), reverse=True)
        recommended = sorted_cats[:2]
    else:
        recommended = observed_values

    return TuningRecommendation(
        parameter=param,
        parameter_type='categorical',
        current_range=observed_values,
        recommended_range=recommended,
        rationale=rationale,
        confidence=min(0.85, 0.5 + sensitivity.importance_score * 0.35),
        priority='high' if sensitivity.importance_score > 0.5 else 'medium',
        source='sensitivity',
    )


def _recommend_from_pareto_knee(
    runs: List[dict],
    pareto_response: ParetoFrontierResponse,
    objectives: List[ObjectiveConfig],
) -> List[TuningRecommendation]:
    """Generate recommendations from Pareto knee point configuration."""
    recommendations = []
    knee_hps = _get_knee_point_hyperparameters(runs, pareto_response.knee_point)
    if not knee_hps:
        return recommendations

    # Get all observed ranges for parameters present in knee point
    all_params = set()
    for r in runs:
        all_params.update(r.get('hyperparameters', {}).keys())

    for param, knee_val in knee_hps.items():
        if param not in all_params:
            continue
        observed_range = _get_observed_range(runs, param)

        if isinstance(observed_range, tuple):
            # Numeric parameter
            curr_min, curr_max = observed_range
            if curr_min == curr_max:
                continue

            # Suggest narrowing range around knee point value
            range_span = curr_max - curr_min
            # Narrow to ±20% of current range around knee value
            margin = range_span * 0.2
            new_min = max(curr_min, knee_val - margin)
            new_max = min(curr_max, knee_val + margin)

            # If knee is at boundary, expand outward from that boundary
            if knee_val <= curr_min + range_span * 0.1:
                # Knee at lower bound - expand upward
                new_max = curr_max
                new_min = curr_min
            elif knee_val >= curr_max - range_span * 0.1:
                # Knee at upper bound - expand downward
                new_min = curr_min
                new_max = curr_max

            rationale = f"Pareto knee point configuration uses {param}={knee_val:.4f}. This represents the optimal trade-off across objectives {[f'{o.metric} ({o.direction})' for o in objectives]}. Consider focusing search near this value."

            recommendations.append(TuningRecommendation(
                parameter=param,
                parameter_type='numeric',
                current_range=observed_range,
                recommended_range=(round(new_min, 4), round(new_max, 4)),
                rationale=rationale,
                confidence=0.75,
                priority='high',
                source='pareto_knee',
            ))
        else:
            # Categorical parameter
            rationale = f"Pareto knee point uses {param}='{knee_val}'. This category achieves the best multi-objective trade-off. Prioritize this category in future searches."

            recommendations.append(TuningRecommendation(
                parameter=param,
                parameter_type='categorical',
                current_range=observed_range,
                recommended_range=[knee_val] if knee_val in observed_range else observed_range,
                rationale=rationale,
                confidence=0.8,
                priority='high',
                source='pareto_knee',
            ))

    return recommendations


def generate_tuning_recommendations(
    runs: List[dict],
    sensitivity_response: SensitivityResponse,
    pareto_response: Optional[ParetoFrontierResponse] = None,
    objectives: Optional[List[ObjectiveConfig]] = None,
) -> TuningRecommendationsResponse:
    """Generate hyperparameter tuning recommendations from sensitivity and Pareto analysis.

    Args:
        runs: List of run dicts with hyperparameters and metrics
        sensitivity_response: Output from sensitivity analysis
        pareto_response: Optional Pareto frontier result for knee point recommendations
        objectives: Objectives used for Pareto analysis (required if pareto_response provided)

    Returns:
        TuningRecommendationsResponse with prioritized recommendations
    """
    recommendations = []
    target_metric = sensitivity_response.target_metric

    # Build sensitivity lookup
    sensitivity_map = {p.parameter: p for p in sensitivity_response.parameters}

    # Get all unique parameters from runs
    all_params = set()
    for r in runs:
        all_params.update(r.get('hyperparameters', {}).keys())

    # 1. Recommendations from sensitivity analysis
    for param in sorted(all_params):
        sensitivity = sensitivity_map.get(param)
        if not sensitivity:
            continue

        observed_range = _get_observed_range(runs, param)

        if sensitivity.parameter_type == 'numeric' and isinstance(observed_range, tuple):
            rec = _recommend_numeric_range_from_sensitivity(
                param, sensitivity, observed_range, target_metric,
                'maximize'  # default direction; sensitivity correlation already accounts for direction
            )
            if rec:
                recommendations.append(rec)
        elif sensitivity.parameter_type == 'categorical' and isinstance(observed_range, list):
            rec = _recommend_categorical_from_sensitivity(
                param, sensitivity, observed_range, runs, target_metric
            )
            if rec:
                recommendations.append(rec)

    # 2. Recommendations from Pareto knee point (if available)
    if pareto_response and objectives:
        pareto_recs = _recommend_from_pareto_knee(runs, pareto_response, objectives)
        # Merge with existing recommendations, preferring Pareto for conflicts
        for p_rec in pareto_recs:
            existing_idx = next((i for i, r in enumerate(recommendations) if r.parameter == p_rec.parameter), None)
            if existing_idx is not None:
                # Combine rationale, use Pareto as primary source
                combined = recommendations[existing_idx]
                combined.rationale = f"{p_rec.rationale} Additionally, {combined.rationale}"
                combined.confidence = max(combined.confidence, p_rec.confidence)
                combined.priority = 'high'
                combined.source = 'combined'
            else:
                recommendations.append(p_rec)

    # 3. Sort by priority and confidence
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations.sort(key=lambda r: (priority_order.get(r.priority, 3), -r.confidence))

    # Build sensitivity summary
    sensitivity_summary = {
        "total_parameters_analyzed": len(sensitivity_response.parameters),
        "influential_parameters": len([p for p in sensitivity_response.parameters if p.importance_score >= 0.1]),
        "top_parameters": [
            {"parameter": p.parameter, "importance": p.importance_score, "type": p.parameter_type}
            for p in sensitivity_response.parameters[:5]
        ],
    }

    pareto_knee_config = None
    if pareto_response and pareto_response.knee_point:
        knee_hps = _get_knee_point_hyperparameters(runs, pareto_response.knee_point)
        if knee_hps:
            pareto_knee_config = {
                "run_id": pareto_response.knee_point.run_id,
                "run_name": pareto_response.knee_point.run_name,
                "variant_name": pareto_response.knee_point.variant_name,
                "hyperparameters": knee_hps,
                "metrics": pareto_response.knee_point.metrics,
                "normalized_distance_to_utopia": pareto_response.knee_point.normalized_distance_to_utopia,
            }

    return TuningRecommendationsResponse(
        experiment_id=sensitivity_response.experiment_id,
        target_metric=target_metric,
        recommendations=recommendations,
        sensitivity_summary=sensitivity_summary,
        pareto_knee_config=pareto_knee_config,
    )