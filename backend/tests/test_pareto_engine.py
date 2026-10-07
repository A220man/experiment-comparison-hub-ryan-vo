"""Tests for multi-objective Pareto frontier engine, hypervolume indicator, and knee detection."""

from backend.app.models.schemas import ObjectiveConfig
from backend.app.services.pareto_engine import calculate_pareto_frontier, is_dominating


def test_is_dominating_logic():
    """Verify Pareto dominance condition across maximize and minimize objectives."""
    objectives = [
        ObjectiveConfig(metric="accuracy", direction="maximize"),
        ObjectiveConfig(metric="latency_ms", direction="minimize"),
    ]

    # Run A has higher accuracy and lower latency -> dominates B
    a = {"accuracy": 0.95, "latency_ms": 10.0}
    b = {"accuracy": 0.90, "latency_ms": 15.0}
    assert is_dominating(a, b, objectives) is True
    assert is_dominating(b, a, objectives) is False

    # Trade-off: C has higher accuracy but higher latency -> neither dominates
    c = {"accuracy": 0.98, "latency_ms": 25.0}
    assert is_dominating(a, c, objectives) is False
    assert is_dominating(c, a, objectives) is False


def test_pareto_frontier_2d_and_knee_detection():
    """Test full 2D Pareto frontier calculation and knee compromise point selection."""
    runs = [
        {"id": "r1", "name": "Run-Baseline", "variant_name": "base", "seed": 42, "metrics": {"accuracy": 0.85, "latency_ms": 20.0}},
        {"id": "r2", "name": "Run-Dominated", "variant_name": "slow_low", "seed": 42, "metrics": {"accuracy": 0.80, "latency_ms": 25.0}},
        {"id": "r3", "name": "Run-Fast", "variant_name": "pruned", "seed": 42, "metrics": {"accuracy": 0.84, "latency_ms": 8.0}},
        {"id": "r4", "name": "Run-Accurate", "variant_name": "large", "seed": 42, "metrics": {"accuracy": 0.92, "latency_ms": 30.0}},
        {"id": "r5", "name": "Run-SweetSpot", "variant_name": "lora_mid", "seed": 42, "metrics": {"accuracy": 0.90, "latency_ms": 12.0}},
    ]

    objectives = [
        ObjectiveConfig(metric="accuracy", direction="maximize"),
        ObjectiveConfig(metric="latency_ms", direction="minimize"),
    ]

    result = calculate_pareto_frontier(runs, objectives, "exp-1")

    assert result.total_evaluated_runs == 5
    # r2 is dominated by r1, r3, r5. r1 is dominated by r5 (accuracy 0.90 > 0.85, latency 12 < 20).
    frontier_ids = [p.run_id for p in result.frontier_points]
    assert "r2" not in frontier_ids
    assert "r1" not in frontier_ids
    assert "r3" in frontier_ids  # fastest (8ms)
    assert "r4" in frontier_ids  # most accurate (0.92)
    assert "r5" in frontier_ids  # great compromise

    assert result.frontier_runs_count == 3
    assert result.dominated_runs_count == 2
    assert result.hypervolume_indicator > 0.0

    # Knee point should be selected
    assert result.knee_point is not None
    assert result.knee_point.run_id in frontier_ids


def test_pareto_3d_objectives():
    """Test 3D multi-objective Pareto optimization (accuracy, latency, parameter count)."""
    runs = [
        {"id": "r1", "name": "A", "variant_name": "v1", "seed": 1, "metrics": {"accuracy": 0.90, "latency_ms": 15.0, "params_m": 100.0}},
        {"id": "r2", "name": "B", "variant_name": "v2", "seed": 1, "metrics": {"accuracy": 0.88, "latency_ms": 12.0, "params_m": 50.0}},
        {"id": "r3", "name": "C", "variant_name": "v3", "seed": 1, "metrics": {"accuracy": 0.85, "latency_ms": 5.0, "params_m": 20.0}},
        {"id": "r4", "name": "Dominated", "variant_name": "v4", "seed": 1, "metrics": {"accuracy": 0.80, "latency_ms": 20.0, "params_m": 120.0}},
    ]
    objectives = [
        ObjectiveConfig(metric="accuracy", direction="maximize"),
        ObjectiveConfig(metric="latency_ms", direction="minimize"),
        ObjectiveConfig(metric="params_m", direction="minimize"),
    ]

    res = calculate_pareto_frontier(runs, objectives, "exp-3d")
    assert res.total_evaluated_runs == 4
    assert res.frontier_runs_count == 3
    assert res.hypervolume_indicator > 0.0


def test_pareto_empty_and_single_input():
    """Verify robust handling of empty runs and single-run inputs."""
    objectives = [
        ObjectiveConfig(metric="acc", direction="maximize"),
        ObjectiveConfig(metric="loss", direction="minimize"),
    ]

    empty_res = calculate_pareto_frontier([], objectives, "exp-0")
    assert empty_res.total_evaluated_runs == 0
    assert empty_res.frontier_runs_count == 0
    assert empty_res.knee_point is None

    single_run = [{"id": "s1", "name": "Only", "variant_name": "v", "seed": 42, "metrics": {"acc": 0.9, "loss": 0.2}}]
    single_res = calculate_pareto_frontier(single_run, objectives, "exp-single")
    assert single_res.total_evaluated_runs == 1
    assert single_res.frontier_runs_count == 1
    assert single_res.knee_point is not None
    assert single_res.knee_point.run_id == "s1"
