"""Tests for boundary conditions, extreme values, and malformed inputs."""

import pytest
from backend.app.models.schemas import ObjectiveConfig, RunCreate
from backend.app.services.pareto_engine import calculate_pareto_frontier
from backend.app.services.statistics_engine import run_cross_seed_analysis


def test_malformed_run_metrics_rejected_by_schema():
    """Ensure non-numeric metric values are rejected with validation error."""
    with pytest.raises(Exception):
        RunCreate(
            experiment_id="exp_1",
            name="Malformed Run",
            variant_name="bad",
            metrics={"accuracy": "not-a-number"},
        )


def test_pareto_with_identical_objective_values():
    """Verify Pareto engine handles solutions where all metrics are identical without division-by-zero."""
    runs = [
        {"id": "r1", "name": "Run1", "variant_name": "v1", "seed": 1, "metrics": {"acc": 0.85, "lat": 10.0}},
        {"id": "r2", "name": "Run2", "variant_name": "v2", "seed": 2, "metrics": {"acc": 0.85, "lat": 10.0}},
    ]
    objectives = [
        ObjectiveConfig(metric="acc", direction="maximize"),
        ObjectiveConfig(metric="lat", direction="minimize"),
    ]
    res = calculate_pareto_frontier(runs, objectives, "exp-identical")
    assert res.total_evaluated_runs == 2
    assert res.frontier_runs_count == 2
    assert res.knee_point is not None


def test_cross_seed_zero_variance_samples():
    """Ensure Welch's t-test handles identical values within groups gracefully without error."""
    runs = [
        {"variant_name": "const_base", "seed": 1, "metrics": {"loss": 0.50}},
        {"variant_name": "const_base", "seed": 2, "metrics": {"loss": 0.50}},
        {"variant_name": "const_base", "seed": 3, "metrics": {"loss": 0.50}},
        {"variant_name": "const_treat", "seed": 1, "metrics": {"loss": 0.20}},
        {"variant_name": "const_treat", "seed": 2, "metrics": {"loss": 0.20}},
        {"variant_name": "const_treat", "seed": 3, "metrics": {"loss": 0.20}},
    ]
    res = run_cross_seed_analysis(runs, "const_base", ["loss"], "exp-zero-var")
    assert len(res.hypothesis_tests) == 1
    test_res = res.hypothesis_tests[0]
    assert test_res.mean_delta == -0.30
    assert test_res.is_statistically_significant is True
