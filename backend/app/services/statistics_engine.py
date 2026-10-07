import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats
from backend.app.models.schemas import ConfidenceInterval, CrossSeedResponse, HypothesisTestResult, SeedAggregatedMetric
from backend.app.services.experiment_service import is_lower_better

def compute_bootstrap_ci(values: np.ndarray, n_resamples: int = 2000, confidence_level: float = 0.95, seed: int = 42) -> Tuple[float, float]:
    n = len(values)
    if n < 2: return (float(values[0]) if n == 1 else 0.0, float(values[0]) if n == 1 else 0.0)
    rng = np.random.RandomState(seed)
    res = np.mean(rng.choice(values, size=(n_resamples, n), replace=True), axis=1)
    a = 1.0 - confidence_level
    return (float(np.percentile(res, 100.0 * (a / 2.0))), float(np.percentile(res, 100.0 * (1.0 - a / 2.0))))

def compute_t_distribution_ci(values: np.ndarray, confidence_level: float = 0.95) -> Tuple[float, float]:
    n = len(values)
    if n < 2: return (float(values[0]) if n == 1 else 0.0, float(values[0]) if n == 1 else 0.0)
    m = float(np.mean(values))
    margin = stats.t.ppf((1.0 + confidence_level) / 2.0, df=n - 1) * float(stats.sem(values))
    return (m - margin, m + margin)

def compute_cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    return 0.0 if nx == 0 or ny == 0 else (sum(1 for xi in x for yj in y if xi > yj) - sum(1 for xi in x for yj in y if xi < yj)) / (nx * ny)

def compute_cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2: return 0.0
    p = math.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    return float((np.mean(y) - np.mean(x)) / p) if p != 0 else 0.0

def aggregate_variant_metrics(variant_runs: List[dict], metrics_to_eval: List[str]) -> List[SeedAggregatedMetric]:
    if not variant_runs: return []
    v_name, seeds, aggs = variant_runs[0]['variant_name'], [r['seed'] for r in variant_runs], []
    for m in metrics_to_eval:
        vals = [float(r['metrics'][m]) for r in variant_runs if m in r.get('metrics', {}) and isinstance(r['metrics'][m], (int, float))]
        if not vals: continue
        arr = np.array(vals, dtype=np.float64)
        n = len(arr)
        mean, s = float(np.mean(arr)), (float(np.std(arr, ddof=1)) if n > 1 else 0.0)
        q75, q25 = np.percentile(arr, [75, 25])
        t_lo, t_hi = compute_t_distribution_ci(arr, 0.95)
        b_lo, b_hi = compute_bootstrap_ci(arr, n_resamples=1500, confidence_level=0.95)
        sem = float(stats.sem(arr)) if n > 1 else 0.0
        aggs.append(SeedAggregatedMetric(variant_name=v_name, metric=m, sample_size_n=n, mean=round(mean, 5), std_dev=round(s, 5), median=round(float(np.median(arr)), 5), iqr=round(float(q75 - q25), 5), min_value=round(float(np.min(arr)), 5), max_value=round(float(np.max(arr)), 5), standard_error=round(sem, 5), ci_t_distribution=ConfidenceInterval(lower=round(t_lo, 5), upper=round(t_hi, 5), confidence_level=0.95, method='student_t'), ci_bootstrap=ConfidenceInterval(lower=round(b_lo, 5), upper=round(b_hi, 5), confidence_level=0.95, method='empirical_bootstrap'), seeds=seeds))
    return aggs

def run_cross_seed_analysis(runs: List[dict], baseline_variant: Optional[str], metrics_to_eval: List[str], experiment_id: str, alpha: float = 0.05) -> CrossSeedResponse:
    v_dict: Dict[str, List[dict]] = {}
    for r in runs:
        if r.get('variant_name'): v_dict.setdefault(r['variant_name'], []).append(r)
    v_names = list(v_dict.keys())
    if not v_names:
        return CrossSeedResponse(experiment_id=experiment_id, baseline_variant='', variants_evaluated=[], metrics_evaluated=metrics_to_eval, aggregations=[], hypothesis_tests=[], sample_size_warnings=['No runs found for experiment.'])
    base = baseline_variant if baseline_variant in v_dict else v_names[0]
    aggs, warnings = [], []
    for vn, vr in v_dict.items():
        if len(vr) < 3: warnings.append(f"Variant '{vn}' has only {len(vr)} seed(s); 3–5 recommended.")
        aggs.extend(aggregate_variant_metrics(vr, metrics_to_eval))
    base_runs = v_dict.get(base, [])
    tests = []
    for t_name, t_runs in v_dict.items():
        if t_name == base: continue
        for m in metrics_to_eval:
            bv = [float(r['metrics'][m]) for r in base_runs if m in r.get('metrics', {})]
            tv = [float(r['metrics'][m]) for r in t_runs if m in r.get('metrics', {})]
            if len(bv) < 2 or len(tv) < 2: continue
            ab, at = np.array(bv, dtype=np.float64), np.array(tv, dtype=np.float64)
            bm, tm = float(np.mean(ab)), float(np.mean(at))
            delta = tm - bm
            pct = delta / abs(bm) * 100.0 if bm != 0 else 0.0
            tres = stats.ttest_ind(at, ab, equal_var=False)
            p_w = float(tres.pvalue) if not np.isnan(tres.pvalue) else 1.0
            t_stat = float(tres.statistic) if not np.isnan(tres.statistic) else 0.0
            try: mw_res = stats.mannwhitneyu(at, ab, alternative='two-sided'); p_mw = float(mw_res.pvalue) if not np.isnan(mw_res.pvalue) else 1.0
            except Exception: p_mw = 1.0
            d_val = compute_cohens_d(ab, at)
            c_val = compute_cliffs_delta(at, ab)
            sig = p_w < alpha
            better = delta < 0 if is_lower_better(m) else delta > 0
            lbl = ('Significant Improvement' if better else 'Significant Degradation') if sig else 'Inconclusive / Seed Variance'
            concl = f"{t_name} vs {base} on {m}: {lbl} (p={p_w:.4f}, d={d_val:.2f})"
            tests.append(HypothesisTestResult(baseline_variant=base, treatment_variant=t_name, metric=m, baseline_mean=round(bm, 5), treatment_mean=round(tm, 5), mean_delta=round(delta, 5), percent_change=round(pct, 3), t_statistic=round(t_stat, 4), p_value_welch=round(p_w, 5), p_value_mann_whitney=round(p_mw, 5), cohens_d=round(d_val, 3), cliffs_delta=round(c_val, 3), is_statistically_significant=sig, significance_label=lbl, conclusion=concl))
    return CrossSeedResponse(experiment_id=experiment_id, baseline_variant=base, variants_evaluated=v_names, metrics_evaluated=metrics_to_eval, aggregations=aggs, hypothesis_tests=tests, sample_size_warnings=warnings)
