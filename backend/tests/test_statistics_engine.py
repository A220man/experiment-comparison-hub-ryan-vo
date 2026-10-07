"""Tests for multi-seed statistical aggregation, confidence intervals, Welch's t-test, and effect sizes."""

import numpy as np
from backend.app.services.statistics_engine import (
    compute_bootstrap_ci,
    compute_cliffs_delta,
    compute_cohens_d,
    compute_t_distribution_ci,
    run_cross_seed_analysis,
)


def test_confidence_intervals_calculation():
    """Verify Student's t and empirical bootstrap confidence intervals."""
    # Synthetic samples with known mean ~ 10.0
    arr = np.array([9.8, 10.1, 9.9, 10.2, 10.0], dtype=np.float64)

    t_low, t_high = compute_t_distribution_ci(arr, 0.95)
    assert t_low < 10.0 < t_high

    b_low, b_high = compute_bootstrap_ci(arr, n_resamples=1000, confidence_level=0.95, seed=42)
    assert b_low < 10.0 < b_high


def test_cross_seed_significant_improvement():
    """Verify Welch's t-test detects statistically significant outperformance across seeds."""
    baseline_runs = [
        {"variant_name": "baseline", "seed": 1, "metrics": {"accuracy": 0.75, "val_loss": 0.50}},
        {"variant_name": "baseline", "seed": 2, "metrics": {"accuracy": 0.76, "val_loss": 0.49}},
        {"variant_name": "baseline", "seed": 3, "metrics": {"accuracy": 0.74, "val_loss": 0.51}},
        {"variant_name": "baseline", "seed": 4, "metrics": {"accuracy": 0.75, "val_loss": 0.50}},
        {"variant_name": "baseline", "seed": 5, "metrics": {"accuracy": 0.75, "val_loss": 0.50}},
    ]
    treatment_runs = [
        {"variant_name": "treatment_lora", "seed": 1, "metrics": {"accuracy": 0.88, "val_loss": 0.32}},
        {"variant_name": "treatment_lora", "seed": 2, "metrics": {"accuracy": 0.89, "val_loss": 0.31}},
        {"variant_name": "treatment_lora", "seed": 3, "metrics": {"accuracy": 0.87, "val_loss": 0.33}},
        {"variant_name": "treatment_lora", "seed": 4, "metrics": {"accuracy": 0.88, "val_loss": 0.32}},
        {"variant_name": "treatment_lora", "seed": 5, "metrics": {"accuracy": 0.88, "val_loss": 0.32}},
    ]

    all_runs = baseline_runs + treatment_runs
    res = run_cross_seed_analysis(all_runs, "baseline", ["accuracy", "val_loss"], "exp-stats", alpha=0.05)

    assert len(res.aggregations) == 4  # 2 variants * 2 metrics
    assert len(res.hypothesis_tests) == 2

    acc_test = next(t for t in res.hypothesis_tests if t.metric == "accuracy")
    assert acc_test.is_statistically_significant is True
    assert acc_test.p_value_welch < 0.001
    assert "Significant Improvement" in acc_test.significance_label
    assert acc_test.cohens_d > 2.0  # massive effect size

    loss_test = next(t for t in res.hypothesis_tests if t.metric == "val_loss")
    assert loss_test.is_statistically_significant is True
    assert "Significant Improvement" in loss_test.significance_label


def test_cross_seed_inconclusive_seed_variance():
    """Verify Welch's t-test correctly identifies overlapping distributions as random seed noise."""
    baseline_runs = [
        {"variant_name": "base", "seed": 1, "metrics": {"accuracy": 0.82}},
        {"variant_name": "base", "seed": 2, "metrics": {"accuracy": 0.85}},
        {"variant_name": "base", "seed": 3, "metrics": {"accuracy": 0.81}},
        {"variant_name": "base", "seed": 4, "metrics": {"accuracy": 0.84}},
    ]
    candidate_runs = [
        {"variant_name": "cand", "seed": 1, "metrics": {"accuracy": 0.83}},
        {"variant_name": "cand", "seed": 2, "metrics": {"accuracy": 0.82}},
        {"variant_name": "cand", "seed": 3, "metrics": {"accuracy": 0.84}},
        {"variant_name": "cand", "seed": 4, "metrics": {"accuracy": 0.83}},
    ]

    all_runs = baseline_runs + candidate_runs
    res = run_cross_seed_analysis(all_runs, "base", ["accuracy"], "exp-noisy", alpha=0.05)

    acc_test = res.hypothesis_tests[0]
    assert acc_test.is_statistically_significant is False
    assert acc_test.p_value_welch >= 0.05
    assert "Inconclusive" in acc_test.significance_label


def test_sample_size_warnings():
    """Ensure warnings are raised when variants have fewer than 3 seeds."""
    runs = [
        {"variant_name": "underpowered_variant", "seed": 1, "metrics": {"accuracy": 0.80}},
        {"variant_name": "underpowered_variant", "seed": 2, "metrics": {"accuracy": 0.82}},
    ]
    res = run_cross_seed_analysis(runs, "underpowered_variant", ["accuracy"], "exp-warn")
    assert len(res.sample_size_warnings) > 0
    assert "underpowered_variant" in res.sample_size_warnings[0]
