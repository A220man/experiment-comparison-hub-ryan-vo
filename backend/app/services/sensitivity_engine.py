import math
from typing import Dict, List, Optional
import numpy as np
from scipy import stats
from backend.app.models.schemas import ParameterSensitivity, SensitivityResponse

def analyze_parameter_sensitivity(runs: List[dict], target_metric: str, experiment_id: str) -> SensitivityResponse:
    valid_runs = [r for r in runs if target_metric in r.get('metrics', {}) and isinstance(r['metrics'][target_metric], (int, float))]
    if len(valid_runs) < 2:
        return SensitivityResponse(experiment_id=experiment_id, target_metric=target_metric, total_runs_analyzed=len(valid_runs), parameters=[])
    metric_values = np.array([float(r['metrics'][target_metric]) for r in valid_runs], dtype=np.float64)
    param_keys = set()
    for r in valid_runs:
        for k in r.get('hyperparameters', {}).keys():
            param_keys.add(k)
    results: List[ParameterSensitivity] = []
    for param in sorted(param_keys):
        raw_vals = [r.get('hyperparameters', {}).get(param) for r in valid_runs]
        indices = [i for i, v in enumerate(raw_vals) if v is not None]
        if len(indices) < 2:
            continue
        sample_vals = [raw_vals[i] for i in indices]
        y = metric_values[indices]
        is_numeric = all((isinstance(v, (int, float)) and (not isinstance(v, bool)) for v in sample_vals))
        if is_numeric:
            x = np.array([float(v) for v in sample_vals], dtype=np.float64)
            if np.std(x) == 0 or np.std(y) == 0:
                continue
            try:
                r_val, _ = stats.pearsonr(x, y)
                rho_val, _ = stats.spearmanr(x, y)
                if np.isnan(r_val):
                    r_val = 0.0
                if np.isnan(rho_val):
                    rho_val = 0.0
            except Exception:
                r_val, rho_val = (0.0, 0.0)
            importance = abs(rho_val)
            direction = 'positive' if rho_val > 0.2 else 'negative' if rho_val < -0.2 else 'negligible'
            summary = f"Numeric hyperparameter '{param}' exhibits {direction} correlation (Spearman rho={rho_val:.3f}, Pearson r={r_val:.3f}) with {target_metric}."
            results.append(ParameterSensitivity(parameter=param, parameter_type='numeric', pearson_r=round(float(r_val), 4), spearman_rho=round(float(rho_val), 4), importance_score=round(float(importance), 4), summary=summary))
        else:
            groups: Dict[str, List[float]] = {}
            for v, metric_val in zip(sample_vals, y):
                groups.setdefault(str(v), []).append(float(metric_val))
            if len(groups) < 2:
                continue
            group_lists = [v for v in groups.values() if len(v) > 0]
            if len(group_lists) < 2:
                continue
            try:
                f_stat, p_val = stats.f_oneway(*group_lists)
                if np.isnan(f_stat):
                    f_stat = 0.0
                importance = min(1.0, float(f_stat) / (10.0 + float(f_stat)))
            except Exception:
                f_stat, importance = (0.0, 0.0)
            best_group = max(groups.keys(), key=lambda k: np.mean(groups[k]))
            summary = f"Categorical parameter '{param}' across {len(groups)} distinct categories. Top performing group: '{best_group}' (mean {np.mean(groups[best_group]):.3f})."
            results.append(ParameterSensitivity(parameter=param, parameter_type='categorical', pearson_r=None, spearman_rho=None, importance_score=round(float(importance), 4), summary=summary))
    results.sort(key=lambda p: p.importance_score, reverse=True)
    return SensitivityResponse(experiment_id=experiment_id, target_metric=target_metric, total_runs_analyzed=len(valid_runs), parameters=results)
