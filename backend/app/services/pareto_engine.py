import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from backend.app.models.schemas import ObjectiveConfig, ParetoFrontierResponse, ParetoPoint

def is_dominating(a: Dict[str, float], b: Dict[str, float], objectives: List[ObjectiveConfig]) -> bool:
    better = False
    for obj in objectives:
        va, vb = a.get(obj.metric), b.get(obj.metric)
        if va is None or vb is None: return False
        if obj.direction == 'maximize':
            if va < vb: return False
            if va > vb: better = True
        else:
            if va > vb: return False
            if va < vb: better = True
    return better

def aggregate_runs_by_variant(runs: List[dict], objectives: List[ObjectiveConfig], method: str = 'mean') -> List[dict]:
    v_dict: Dict[str, List[dict]] = {}
    for r in runs:
        if all(obj.metric in r.get('metrics', {}) and isinstance(r['metrics'][obj.metric], (int, float)) for obj in objectives):
            v_dict.setdefault(r.get('variant_name', 'default'), []).append(r)
    agg = []
    for vn, vr in sorted(v_dict.items()):
        seeds = [r.get('seed', 0) for r in vr]
        m_dict: Dict[str, float] = {}
        for obj in objectives:
            vals = [float(r['metrics'][obj.metric]) for r in vr]
            m_dict[obj.metric] = float(np.median(vals) if method == 'median' else np.mean(vals))
        agg.append({'id': f'var_{vn}', 'name': f'{vn} ({method}, N={len(vr)})', 'variant_name': vn, 'seed': seeds[0] if len(seeds) == 1 else 0, 'metrics': m_dict, 'sample_size_n': len(vr), 'seeds': seeds})
    return agg

def calculate_pareto_frontier(runs_data: List[dict], objectives: List[ObjectiveConfig], experiment_id: str, is_aggregated: bool = False, aggregation_method: Optional[str] = None) -> ParetoFrontierResponse:
    valid = [r for r in runs_data if all(obj.metric in r.get('metrics', {}) and isinstance(r['metrics'][obj.metric], (int, float)) for obj in objectives)]
    if not valid:
        return ParetoFrontierResponse(experiment_id=experiment_id, objectives=objectives, all_points=[], frontier_points=[], knee_point=None, hypervolume_indicator=0.0, total_evaluated_runs=0, frontier_runs_count=0, dominated_runs_count=0, is_aggregated=is_aggregated, aggregation_method=aggregation_method)
    n = len(valid)
    f_idx = [i for i in range(n) if not any(j != i and is_dominating(valid[j]['metrics'], valid[i]['metrics'], objectives) for j in range(n))]
    k_idx, dists = identify_knee_point(valid, f_idx, objectives)
    points, frontier = [], []
    for i, r in enumerate(valid):
        pt = ParetoPoint(run_id=r['id'], run_name=r['name'], variant_name=r['variant_name'], seed=r['seed'], metrics={obj.metric: float(r['metrics'][obj.metric]) for obj in objectives}, is_frontier=(i in f_idx), is_knee_point=(i == k_idx), normalized_distance_to_utopia=dists.get(i), sample_size_n=r.get('sample_size_n'), seeds=r.get('seeds'))
        points.append(pt)
        if i in f_idx: frontier.append(pt)
    o0 = objectives[0]
    frontier.sort(key=lambda p: p.metrics[o0.metric], reverse=(o0.direction == 'maximize'))
    hv = compute_hypervolume(valid, f_idx, objectives)
    knee = next((p for p in frontier if p.is_knee_point), None)
    return ParetoFrontierResponse(experiment_id=experiment_id, objectives=objectives, all_points=points, frontier_points=frontier, knee_point=knee, hypervolume_indicator=round(hv, 4), total_evaluated_runs=len(points), frontier_runs_count=len(frontier), dominated_runs_count=len(points) - len(frontier), is_aggregated=is_aggregated, aggregation_method=aggregation_method)

def _normalize_metric(val: float, mn: float, mx: float, direction: str) -> float:
    span = mx - mn
    return 1.0 if span == 0 else ((val - mn) / span if direction == 'maximize' else (mx - val) / span)

def identify_knee_point(runs: List[dict], f_idx: List[int], objectives: List[ObjectiveConfig]) -> Tuple[Optional[int], Dict[int, float]]:
    if not f_idx: return (None, {})
    if len(f_idx) == 1: return (f_idx[0], {f_idx[0]: 0.0})
    b = {obj.metric: (min(runs[i]['metrics'][obj.metric] for i in f_idx), max(runs[i]['metrics'][obj.metric] for i in f_idx)) for obj in objectives}
    dists, best, min_d = {}, None, float('inf')
    for idx in f_idx:
        sq = sum((1.0 - _normalize_metric(runs[idx]['metrics'][obj.metric], b[obj.metric][0], b[obj.metric][1], obj.direction)) ** 2 for obj in objectives)
        d = round(math.sqrt(sq), 4)
        dists[idx] = d
        if d < min_d: min_d, best = d, idx
    return (best, dists)

def compute_hypervolume(runs: List[dict], f_idx: List[int], objectives: List[ObjectiveConfig]) -> float:
    if not f_idx: return 0.0
    b = {obj.metric: (min(r['metrics'][obj.metric] for r in runs), max(r['metrics'][obj.metric] for r in runs)) for obj in objectives}
    pts = [[max(0.0, min(1.0, _normalize_metric(runs[idx]['metrics'][obj.metric], b[obj.metric][0], b[obj.metric][1], obj.direction))) for obj in objectives] for idx in f_idx]
    if len(objectives) == 2:
        s_pts = sorted(pts, key=lambda p: p[0])
        return max(0.0, min(1.0, sum((x - (s_pts[i - 1][0] if i > 0 else 0.0)) * max(p[1] for p in s_pts[i:]) for i, (x, y) in enumerate(s_pts))))
    rng = np.random.RandomState(42)
    samples = rng.uniform(0.0, 1.0, size=(5000, len(objectives)))
    return sum(1 for s in samples if any(all(p[k] >= s[k] for k in range(len(objectives))) for p in pts)) / 5000.0
