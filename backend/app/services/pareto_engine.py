import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from backend.app.models.schemas import ObjectiveConfig, ParetoFrontierResponse, ParetoPoint

def is_dominating(metrics_a: Dict[str, float], metrics_b: Dict[str, float], objectives: List[ObjectiveConfig]) -> bool:
    at_least_as_good = True
    strictly_better = False
    for obj in objectives:
        va, vb = metrics_a.get(obj.metric), metrics_b.get(obj.metric)
        if va is None or vb is None:
            return False
        if obj.direction == 'maximize':
            if va < vb:
                at_least_as_good = False; break
            if va > vb:
                strictly_better = True
        else:
            if va > vb:
                at_least_as_good = False; break
            if va < vb:
                strictly_better = True
    return at_least_as_good and strictly_better

def calculate_pareto_frontier(runs_data: List[dict], objectives: List[ObjectiveConfig], experiment_id: str) -> ParetoFrontierResponse:
    valid_runs = [r for r in runs_data if all(obj.metric in r.get('metrics', {}) and isinstance(r['metrics'][obj.metric], (int, float)) for obj in objectives)]
    if not valid_runs:
        return ParetoFrontierResponse(experiment_id=experiment_id, objectives=objectives, all_points=[], frontier_points=[], knee_point=None, hypervolume_indicator=0.0, total_evaluated_runs=0, frontier_runs_count=0, dominated_runs_count=0)
    n = len(valid_runs)
    domination_counts = [0] * n
    for i in range(n):
        for j in range(n):
            if i != j and is_dominating(valid_runs[j]['metrics'], valid_runs[i]['metrics'], objectives):
                domination_counts[i] += 1
    frontier_indices = [i for i, count in enumerate(domination_counts) if count == 0]
    knee_index, normalized_distances = identify_knee_point(valid_runs, frontier_indices, objectives)
    points, frontier_points = [], []
    for i, r in enumerate(valid_runs):
        is_front = i in frontier_indices
        is_knee = (i == knee_index) if knee_index is not None else False
        dist = normalized_distances.get(i)
        pt = ParetoPoint(run_id=r['id'], run_name=r['name'], variant_name=r['variant_name'], seed=r['seed'], metrics={obj.metric: float(r['metrics'][obj.metric]) for obj in objectives}, is_frontier=is_front, is_knee_point=is_knee, normalized_distance_to_utopia=dist)
        points.append(pt)
        if is_front:
            frontier_points.append(pt)
    first_obj = objectives[0]
    frontier_points.sort(key=lambda p: p.metrics[first_obj.metric], reverse=(first_obj.direction == 'maximize'))
    hv = compute_hypervolume(valid_runs, frontier_indices, objectives)
    knee_point_obj = next((p for p in frontier_points if p.is_knee_point), None)
    return ParetoFrontierResponse(experiment_id=experiment_id, objectives=objectives, all_points=points, frontier_points=frontier_points, knee_point=knee_point_obj, hypervolume_indicator=round(hv, 4), total_evaluated_runs=len(points), frontier_runs_count=len(frontier_points), dominated_runs_count=len(points) - len(frontier_points))

def identify_knee_point(runs: List[dict], frontier_indices: List[int], objectives: List[ObjectiveConfig]) -> Tuple[Optional[int], Dict[int, float]]:
    if not frontier_indices:
        return (None, {})
    if len(frontier_indices) == 1:
        return (frontier_indices[0], {frontier_indices[0]: 0.0})
    bounds = {}
    for obj in objectives:
        vals = [r['metrics'][obj.metric] for r in runs]
        bounds[obj.metric] = (min(vals), max(vals))
    distances: Dict[int, float] = {}
    best_index = None
    min_dist = float('inf')
    for idx in frontier_indices:
        r = runs[idx]
        sq_dist = 0.0
        for obj in objectives:
            val = r['metrics'][obj.metric]
            min_v, max_v = bounds[obj.metric]
            span = max_v - min_v
            norm_val = 1.0 if span == 0 else ((val - min_v) / span if obj.direction == 'maximize' else (max_v - val) / span)
            sq_dist += (1.0 - norm_val) ** 2
        euclidean_dist = math.sqrt(sq_dist)
        distances[idx] = round(euclidean_dist, 4)
        if euclidean_dist < min_dist:
            min_dist = euclidean_dist
            best_index = idx
    return (best_index, distances)

def compute_hypervolume(runs: List[dict], frontier_indices: List[int], objectives: List[ObjectiveConfig]) -> float:
    if not frontier_indices:
        return 0.0
    bounds = {obj.metric: (min(r['metrics'][obj.metric] for r in runs), max(r['metrics'][obj.metric] for r in runs)) for obj in objectives}
    normalized_pts: List[List[float]] = []
    for idx in frontier_indices:
        pt = []
        for obj in objectives:
            val = runs[idx]['metrics'][obj.metric]
            min_v, max_v = bounds[obj.metric]
            span = max_v - min_v
            norm = 1.0 if span == 0 else ((val - min_v) / span if obj.direction == 'maximize' else (max_v - val) / span)
            pt.append(max(0.0, min(1.0, norm)))
        normalized_pts.append(pt)
    if len(objectives) == 2:
        pts = sorted(normalized_pts, key=lambda p: p[0])
        area = sum((x - (pts[i - 1][0] if i > 0 else 0.0)) * max(p[1] for p in pts[i:]) for i, (x, y) in enumerate(pts))
        return max(0.0, min(1.0, area))
    num_samples = 5000
    rng = np.random.RandomState(42)
    random_pts = rng.uniform(0.0, 1.0, size=(num_samples, len(objectives)))
    dominated = sum(1 for sample in random_pts if any(all(p[k] >= sample[k] for k in range(len(objectives))) for p in normalized_pts))
    return dominated / num_samples
