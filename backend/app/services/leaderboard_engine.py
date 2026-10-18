"""Multi-metric composite ranking and variant leaderboard engine."""
import math
from typing import Dict, List, Optional
import numpy as np
from backend.app.models.schemas import ObjectiveConfig
from backend.app.services.pareto_engine import aggregate_runs_by_variant, calculate_pareto_frontier
from backend.app.services.statistics_engine import run_cross_seed_analysis

def _norm(val: float, mn: float, mx: float, direction: str) -> float:
    s = mx - mn
    return 0.5 if s == 0 else ((val - mn) / s if direction == "maximize" else (mx - val) / s)

def _pareto_score(var_agg: dict, objectives: List[ObjectiveConfig], vals_by_m: Dict[str, List[float]]) -> float:
    scores = []
    for obj in objectives:
        m = obj.metric
        if m in var_agg.get("metrics", {}) and vals_by_m.get(m):
            v, vals = float(var_agg["metrics"][m]), vals_by_m[m]
            scores.append(_norm(v, min(vals), max(vals), obj.direction))
        else: scores.append(0.0)
    return float(np.mean(scores)) if scores else 0.0

def _sig_score(variant: str, cross_res, objectives: List[ObjectiveConfig], baseline: str, w_d=0.6, w_p=0.4) -> float:
    if variant == baseline: return 0.5
    obj_ms = {obj.metric for obj in objectives}
    tot, n = 0.0, 0
    for t in cross_res.hypothesis_tests:
        if t.treatment_variant != variant or t.metric not in obj_ms: continue
        d = abs(t.cohens_d)
        eff = max(0.0, min(1.0, 2.0 / (1.0 + math.exp(-d)) - 1.0))
        sig = min(1.0, -math.log10(max(t.p_value_welch, 1e-10)) / 5.0)
        is_loss = any(x in t.metric.lower() for x in ("loss", "latency", "error", "perplexity", "memory", "cost", "flop"))
        if (t.mean_delta < 0 if is_loss else t.mean_delta > 0):
            tot += w_d * eff + w_p * sig
            n += 1
    return tot / n if n > 0 else 0.0

def compute_variant_leaderboard(runs_data: List[dict], objectives: List[ObjectiveConfig], baseline_variant: Optional[str], experiment_id: str, aggregate_by_variant: bool = True, aggregation_method: str = "mean", weight_pareto: float = 0.5, weight_significance: float = 0.5) -> dict:
    valid = [r for r in runs_data if all(o.metric in r.get("metrics", {}) and isinstance(r["metrics"][o.metric], (int, float)) for o in objectives)]
    res_base = {"experiment_id": experiment_id, "objectives": [o.model_dump() for o in objectives], "baseline_variant": baseline_variant, "weight_pareto": weight_pareto, "weight_significance": weight_significance, "aggregation_method": aggregation_method if aggregate_by_variant else None, "is_aggregated": aggregate_by_variant}
    if not valid: return {**res_base, "leaderboard": [], "total_variants": 0}
    agg_runs = aggregate_runs_by_variant(valid, objectives, aggregation_method) if aggregate_by_variant else valid
    var_names = sorted({r.get("variant_name", "default") for r in agg_runs})
    base = baseline_variant if baseline_variant in var_names else var_names[0]
    pareto_res = calculate_pareto_frontier(agg_runs, objectives, experiment_id, is_aggregated=aggregate_by_variant, aggregation_method=aggregation_method if aggregate_by_variant else None)
    cross_res = run_cross_seed_analysis(runs=valid, baseline_variant=base, metrics_to_eval=[o.metric for o in objectives], experiment_id=experiment_id)
    vals_by_m = {o.metric: [float(r["metrics"][o.metric]) for r in agg_runs if o.metric in r.get("metrics", {}) and isinstance(r["metrics"][o.metric], (int, float))] for o in objectives}
    lb = []
    for r in agg_runs:
        vn = r.get("variant_name", "default")
        ps = _pareto_score(r, objectives, vals_by_m)
        ss = _sig_score(vn, cross_res, objectives, base)
        comp = weight_pareto * ps + weight_significance * ss
        is_f = any(p.variant_name == vn for p in pareto_res.frontier_points)
        is_k = pareto_res.knee_point is not None and pareto_res.knee_point.variant_name == vn
        v_tests = [t for t in cross_res.hypothesis_tests if t.treatment_variant == vn]
        p_val = float(np.mean([t.p_value_welch for t in v_tests])) if v_tests else 1.0
        d_val = float(np.mean([abs(t.cohens_d) for t in v_tests])) if v_tests else 0.0
        hv_contrib = round(pareto_res.hypervolume_indicator / len(pareto_res.frontier_points), 6) if pareto_res.frontier_points else 0.0
        lb.append({"rank": 0, "variant_name": vn, "composite_score": round(comp, 4), "pareto_score": round(ps, 4), "significance_score": round(ss, 4), "is_frontier": is_f, "is_knee_point": is_k, "is_baseline": vn == base, "metrics": {o.metric: float(r["metrics"].get(o.metric, 0.0)) for o in objectives}, "sample_size_n": r.get("sample_size_n", 1), "seeds": r.get("seeds", [r.get("seed", 0)]), "avg_welch_p_value": round(p_val, 6), "avg_cohens_d": round(d_val, 4), "hypervolume_contribution": hv_contrib})
    lb.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, e in enumerate(lb):
        e["rank"] = lb[i - 1]["rank"] if i > 0 and abs(e["composite_score"] - lb[i - 1]["composite_score"]) < 1e-6 else i + 1
    return {**res_base, "leaderboard": lb, "total_variants": len(lb)}