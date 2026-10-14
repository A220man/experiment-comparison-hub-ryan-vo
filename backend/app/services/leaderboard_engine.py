"""Multi-metric composite ranking and variant leaderboard engine.

Combines normalized Pareto objective scores with cross-seed statistical
significance to produce a deterministic, interpretable variant ranking.
"""
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from backend.app.models.schemas import ObjectiveConfig
from backend.app.services.pareto_engine import (
    calculate_pareto_frontier,
    aggregate_runs_by_variant,
    is_dominating,
)
from backend.app.services.statistics_engine import run_cross_seed_analysis


def _normalize_metric(val: float, mn: float, mx: float, direction: str) -> float:
    """Normalize a metric value to [0, 1] based on direction."""
    span = mx - mn
    if span == 0:
        return 0.5
    if direction == "maximize":
        return (val - mn) / span
    else:
        return (mx - val) / span


def _compute_variant_pareto_score(
    variant_agg: dict,
    objectives: List[ObjectiveConfig],
    all_agg_values: Dict[str, List[float]],
) -> float:
    """Compute normalized Pareto objective score for a variant (0-1)."""
    scores = []
    for obj in objectives:
        metric = obj.metric
        if metric not in variant_agg.get("metrics", {}):
            scores.append(0.0)
            continue
        val = float(variant_agg["metrics"][metric])
        vals = all_agg_values.get(metric, [])
        if not vals:
            scores.append(0.0)
            continue
        mn, mx = min(vals), max(vals)
        scores.append(_normalize_metric(val, mn, mx, obj.direction))
    return float(np.mean(scores)) if scores else 0.0


def _compute_significance_score(
    variant_name: str,
    cross_seed_res,
    objectives: List[ObjectiveConfig],
    baseline_variant: str,
    weight_effect_size: float = 0.6,
    weight_significance: float = 0.4,
) -> float:
    """Compute statistical significance score from cross-seed analysis (0-1).

    Combines effect size magnitude (Cohen's d) with p-value significance.
    """
    if variant_name == baseline_variant:
        # Baseline gets a moderate base score
        return 0.5

    score = 0.0
    count = 0

    for test in cross_seed_res.hypothesis_tests:
        if test.treatment_variant != variant_name:
            continue
        if test.metric not in [obj.metric for obj in objectives]:
            continue

        # Effect size component: sigmoid of Cohen's d (capped at ~3.0)
        d = abs(test.cohens_d)
        effect_score = 2.0 / (1.0 + math.exp(-d)) - 1.0  # maps d=0->0, d=3->~0.95
        effect_score = max(0.0, min(1.0, effect_score))

        # Significance component: -log10(p) scaled
        p = max(test.p_value_welch, 1e-10)
        sig_score = min(1.0, -math.log10(p) / 5.0)  # p=0.001 -> ~0.6, p=1e-5 -> 1.0

        # Only count positive improvements
        better = test.mean_delta > 0 if not any(
            x in test.metric.lower() for x in ("loss", "latency", "error", "perplexity", "memory", "cost", "flop")
        ) else test.mean_delta < 0

        if better:
            score += weight_effect_size * effect_score + weight_significance * sig_score
            count += 1

    return score / count if count > 0 else 0.0


def _compute_composite_score(
    pareto_score: float,
    significance_score: float,
    weight_pareto: float = 0.5,
    weight_significance: float = 0.5,
) -> float:
    """Combine Pareto and significance scores into final composite (0-1)."""
    return weight_pareto * pareto_score + weight_significance * significance_score


def compute_variant_leaderboard(
    runs_data: List[dict],
    objectives: List[ObjectiveConfig],
    baseline_variant: Optional[str],
    experiment_id: str,
    aggregate_by_variant: bool = True,
    aggregation_method: str = "mean",
    weight_pareto: float = 0.5,
    weight_significance: float = 0.5,
) -> dict:
    """Compute multi-metric composite ranking leaderboard for experiment variants.

    Args:
        runs_data: Raw run dictionaries from database
        objectives: List of objective metrics with directions
        baseline_variant: Name of baseline variant for significance testing
        experiment_id: Experiment identifier
        aggregate_by_variant: Whether to aggregate multi-seed runs by variant
        aggregation_method: 'mean' or 'median' for aggregation
        weight_pareto: Weight for normalized Pareto objective score
        weight_significance: Weight for statistical significance score

    Returns:
        Dict with leaderboard entries sorted by composite score (descending)
    """
    # Filter valid runs
    valid_runs = [
        r for r in runs_data
        if all(obj.metric in r.get("metrics", {}) and isinstance(r["metrics"][obj.metric], (int, float)) for obj in objectives)
    ]

    if not valid_runs:
        return {
            "experiment_id": experiment_id,
            "objectives": [obj.model_dump() for obj in objectives],
            "baseline_variant": baseline_variant,
            "leaderboard": [],
            "total_variants": 0,
            "weight_pareto": weight_pareto,
            "weight_significance": weight_significance,
        }

    # Aggregate by variant if requested
    if aggregate_by_variant:
        agg_runs = aggregate_runs_by_variant(valid_runs, objectives, aggregation_method)
    else:
        agg_runs = valid_runs

    # Get unique variant names
    variant_names = sorted(set(r.get("variant_name", "default") for r in agg_runs))
    baseline = baseline_variant if baseline_variant in variant_names else variant_names[0]

    # Compute Pareto frontier on aggregated runs
    pareto_res = calculate_pareto_frontier(
        agg_runs, objectives, experiment_id,
        is_aggregated=aggregate_by_variant,
        aggregation_method=aggregation_method if aggregate_by_variant else None
    )

    # Compute cross-seed analysis
    metrics_to_eval = [obj.metric for obj in objectives]
    cross_res = run_cross_seed_analysis(
        runs=valid_runs,
        baseline_variant=baseline,
        metrics_to_eval=metrics_to_eval,
        experiment_id=experiment_id,
    )

    # Collect all aggregated metric values for normalization
    all_agg_values: Dict[str, List[float]] = {}
    for obj in objectives:
        metric = obj.metric
        all_agg_values[metric] = [
            float(r["metrics"][metric]) for r in agg_runs
            if metric in r.get("metrics", {}) and isinstance(r["metrics"][metric], (int, float))
        ]

    # Build leaderboard entries
    leaderboard = []
    for agg_run in agg_runs:
        variant_name = agg_run.get("variant_name", "default")

        # Pareto score
        pareto_score = _compute_variant_pareto_score(agg_run, objectives, all_agg_values)

        # Significance score
        sig_score = _compute_significance_score(
            variant_name, cross_res, objectives, baseline
        )

        # Composite score
        composite = _compute_composite_score(pareto_score, sig_score, weight_pareto, weight_significance)

        # Find Pareto frontier status
        is_frontier = any(p.variant_name == variant_name for p in pareto_res.frontier_points)
        is_knee = pareto_res.knee_point is not None and pareto_res.knee_point.variant_name == variant_name

        # Collect metric values
        metrics = {obj.metric: float(agg_run["metrics"].get(obj.metric, 0.0)) for obj in objectives}

        # Statistical evidence for this variant
        variant_tests = [t for t in cross_res.hypothesis_tests if t.treatment_variant == variant_name]
        avg_p = np.mean([t.p_value_welch for t in variant_tests]) if variant_tests else 1.0
        avg_d = np.mean([abs(t.cohens_d) for t in variant_tests]) if variant_tests else 0.0

        # Sample size
        sample_size = agg_run.get("sample_size_n", 1)
        seeds = agg_run.get("seeds", [agg_run.get("seed", 0)])

        leaderboard.append({
            "rank": 0,  # Will be set after sorting
            "variant_name": variant_name,
            "composite_score": round(composite, 4),
            "pareto_score": round(pareto_score, 4),
            "significance_score": round(sig_score, 4),
            "is_frontier": is_frontier,
            "is_knee_point": is_knee,
            "is_baseline": variant_name == baseline,
            "metrics": metrics,
            "sample_size_n": sample_size,
            "seeds": seeds,
            "avg_welch_p_value": round(float(avg_p), 6),
            "avg_cohens_d": round(float(avg_d), 4),
            "hypervolume_contribution": round(pareto_res.hypervolume_indicator / len(pareto_res.frontier_points), 6) if pareto_res.frontier_points else 0.0,
        })

    # Sort by composite score descending
    leaderboard.sort(key=lambda x: x["composite_score"], reverse=True)

    # Assign ranks (handle ties)
    for i, entry in enumerate(leaderboard):
        if i > 0 and abs(entry["composite_score"] - leaderboard[i - 1]["composite_score"]) < 1e-6:
            entry["rank"] = leaderboard[i - 1]["rank"]
        else:
            entry["rank"] = i + 1

    return {
        "experiment_id": experiment_id,
        "objectives": [obj.model_dump() for obj in objectives],
        "baseline_variant": baseline,
        "leaderboard": leaderboard,
        "total_variants": len(leaderboard),
        "weight_pareto": weight_pareto,
        "weight_significance": weight_significance,
        "aggregation_method": aggregation_method if aggregate_by_variant else None,
        "is_aggregated": aggregate_by_variant,
    }