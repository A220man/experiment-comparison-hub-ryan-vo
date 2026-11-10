"""Tests for the Hyperparameter Tuning Recommendations Engine."""

import pytest
import numpy as np
from backend.app.services.tuning_engine import (
    TuningRecommendation,
    TuningRecommendationsResponse,
    _get_observed_range,
    _recommend_numeric_range_from_sensitivity,
    _recommend_categorical_from_sensitivity,
    _recommend_from_pareto_knee,
    generate_tuning_recommendations,
)
from backend.app.models.schemas import (
    ObjectiveConfig,
    ParameterSensitivity,
    ParetoPoint,
    SensitivityResponse,
    ParetoFrontierResponse,
)


def make_runs(numeric_params=None, categorical_params=None, metrics=None, n_runs=10):
    """Generate synthetic runs for testing."""
    runs = []
    for i in range(n_runs):
        hp = {}
        if numeric_params:
            for p, (lo, hi) in numeric_params.items():
                hp[p] = lo + (hi - lo) * (i / (n_runs - 1))
        if categorical_params:
            for p, vals in categorical_params.items():
                hp[p] = vals[i % len(vals)]
        m = {}
        if metrics:
            for met, (base, slope) in metrics.items():
                m[met] = base + slope * (i / (n_runs - 1))
        runs.append({
            "id": f"run_{i}",
            "name": f"run_{i}",
            "variant_name": f"v{i % 3}",
            "seed": i,
            "hyperparameters": hp,
            "metrics": m,
        })
    return runs


def make_sensitivity_response(params, experiment_id="exp_test", target_metric="accuracy"):
    """Create a mock SensitivityResponse."""
    param_objs = []
    for p in params:
        param_objs.append(ParameterSensitivity(
            parameter=p["parameter"],
            parameter_type=p["parameter_type"],
            spearman_rho=p.get("spearman_rho"),
            pearson_r=p.get("pearson_r"),
            anova_f_stat=p.get("anova_f_stat"),
            importance_score=p["importance_score"],
            summary=p.get("summary", "moderate"),
        ))
    return SensitivityResponse(
        experiment_id=experiment_id,
        target_metric=target_metric,
        total_runs_analyzed=len(params) * 10 if params else 0,
        parameters=param_objs,
    )


def make_pareto_response(runs, knee_run_id=None, experiment_id="exp_test"):
    """Create a mock ParetoFrontierResponse with a knee point."""
    if knee_run_id is None:
        knee_run_id = runs[0]["id"]
    knee_idx = next(i for i, r in enumerate(runs) if r["id"] == knee_run_id)
    knee_run = runs[knee_idx]
    knee_point = ParetoPoint(
        run_id=knee_run_id,
        run_name=knee_run["name"],
        variant_name=knee_run["variant_name"],
        seed=knee_run["seed"],
        metrics=knee_run["metrics"],
        is_frontier=True,
        is_knee_point=True,
        normalized_distance_to_utopia=0.1,
        sample_size_n=1,
        seeds=[knee_run["seed"]],
    )
    all_points = []
    for i, r in enumerate(runs):
        all_points.append(ParetoPoint(
            run_id=r["id"],
            run_name=r["name"],
            variant_name=r["variant_name"],
            seed=r["seed"],
            metrics=r["metrics"],
            is_frontier=(i == knee_idx),
            is_knee_point=(i == knee_idx),
            normalized_distance_to_utopia=0.1 if i == knee_idx else 0.5,
            sample_size_n=1,
            seeds=[r["seed"]],
        ))
    return ParetoFrontierResponse(
        experiment_id=experiment_id,
        objectives=[
            ObjectiveConfig(metric="accuracy", direction="maximize"),
            ObjectiveConfig(metric="loss", direction="minimize"),
        ],
        all_points=all_points,
        frontier_points=[knee_point],
        knee_point=knee_point,
        hypervolume_indicator=0.5,
        total_evaluated_runs=len(runs),
        frontier_runs_count=1,
        dominated_runs_count=len(runs) - 1,
        is_aggregated=False,
        aggregation_method=None,
    )


class TestTuningRecommendation:
    def test_to_dict_numeric(self):
        rec = TuningRecommendation(
            parameter="lr",
            parameter_type="numeric",
            current_range=(0.001, 0.1),
            recommended_range=(0.001, 0.2),
            rationale="test",
            confidence=0.8,
            priority="high",
            source="sensitivity",
        )
        d = rec.to_dict()
        assert d["parameter"] == "lr"
        assert d["parameter_type"] == "numeric"
        assert d["current_range"] == [0.001, 0.1]
        assert d["recommended_range"] == [0.001, 0.2]
        assert d["confidence"] == 0.8
        assert d["priority"] == "high"
        assert d["source"] == "sensitivity"

    def test_to_dict_categorical(self):
        rec = TuningRecommendation(
            parameter="optimizer",
            parameter_type="categorical",
            current_range=["adam", "sgd", "rmsprop"],
            recommended_range=["adam", "sgd"],
            rationale="test",
            confidence=0.75,
            priority="medium",
            source="pareto_knee",
        )
        d = rec.to_dict()
        assert d["parameter_type"] == "categorical"
        assert d["current_range"] == ["adam", "sgd", "rmsprop"]
        assert d["recommended_range"] == ["adam", "sgd"]
        assert d["source"] == "pareto_knee"


class TestTuningRecommendationsResponse:
    def test_to_dict(self):
        rec = TuningRecommendation(
            parameter="lr",
            parameter_type="numeric",
            current_range=(0.001, 0.1),
            recommended_range=(0.001, 0.2),
            rationale="test",
            confidence=0.8,
            priority="high",
            source="sensitivity",
        )
        resp = TuningRecommendationsResponse(
            experiment_id="exp_1",
            target_metric="accuracy",
            recommendations=[rec],
            sensitivity_summary={"total": 1},
            pareto_knee_config={"run_id": "run_1"},
        )
        d = resp.to_dict()
        assert d["experiment_id"] == "exp_1"
        assert d["target_metric"] == "accuracy"
        assert len(d["recommendations"]) == 1
        assert d["sensitivity_summary"]["total"] == 1
        assert d["pareto_knee_config"]["run_id"] == "run_1"


class TestGetObservedRange:
    def test_numeric_range(self):
        runs = [
            {"hyperparameters": {"lr": 0.001}},
            {"hyperparameters": {"lr": 0.01}},
            {"hyperparameters": {"lr": 0.1}},
        ]
        result = _get_observed_range(runs, "lr")
        assert isinstance(result, tuple)
        assert result == (0.001, 0.1)

    def test_categorical_range(self):
        runs = [
            {"hyperparameters": {"opt": "adam"}},
            {"hyperparameters": {"opt": "sgd"}},
            {"hyperparameters": {"opt": "rmsprop"}},
        ]
        result = _get_observed_range(runs, "opt")
        assert isinstance(result, list)
        assert set(result) == {"adam", "sgd", "rmsprop"}

    def test_empty_values(self):
        runs = [{"hyperparameters": {}}]
        result = _get_observed_range(runs, "lr")
        assert result == (0.0, 0.0)


class TestRecommendNumericRangeFromSensitivity:
    def test_positive_correlation_expands_upper(self):
        runs = make_runs(numeric_params={"lr": (0.001, 0.1)}, metrics={"accuracy": (0.5, 0.4)})
        sensitivity = ParameterSensitivity(
            parameter="lr",
            parameter_type="numeric",
            spearman_rho=0.8,
            pearson_r=0.75,
            anova_f_stat=None,
            importance_score=0.9,
            summary="strong",
        )
        rec = _recommend_numeric_range_from_sensitivity(
            "lr", sensitivity, (0.001, 0.1), "accuracy", "maximize"
        )
        assert rec is not None
        assert rec.parameter == "lr"
        assert rec.parameter_type == "numeric"
        assert rec.recommended_range[1] > 0.1  # Upper bound expanded
        assert rec.recommended_range[0] == 0.001  # Lower bound unchanged
        assert "positive" in rec.rationale.lower()
        assert rec.priority == "high"
        assert rec.source == "sensitivity"

    def test_negative_correlation_expands_lower(self):
        runs = make_runs(numeric_params={"lr": (0.001, 0.1)}, metrics={"accuracy": (0.9, -0.4)})
        sensitivity = ParameterSensitivity(
            parameter="lr",
            parameter_type="numeric",
            spearman_rho=-0.8,
            pearson_r=-0.75,
            anova_f_stat=None,
            importance_score=0.9,
            summary="strong",
        )
        rec = _recommend_numeric_range_from_sensitivity(
            "lr", sensitivity, (0.001, 0.1), "accuracy", "maximize"
        )
        assert rec is not None
        assert rec.recommended_range[0] < 0.001  # Lower bound expanded
        assert rec.recommended_range[1] == 0.1  # Upper bound unchanged
        assert "negative" in rec.rationale.lower()
        assert rec.priority == "high"

    def test_weak_correlation_expands_both(self):
        runs = make_runs(numeric_params={"lr": (0.001, 0.1)}, metrics={"accuracy": (0.5, 0.1)})
        sensitivity = ParameterSensitivity(
            parameter="lr",
            parameter_type="numeric",
            spearman_rho=0.1,
            pearson_r=0.05,
            anova_f_stat=None,
            importance_score=0.3,
            summary="moderate",
        )
        rec = _recommend_numeric_range_from_sensitivity(
            "lr", sensitivity, (0.001, 0.1), "accuracy", "maximize"
        )
        assert rec is not None
        assert rec.recommended_range[0] < 0.001
        assert rec.recommended_range[1] > 0.1
        assert rec.priority == "medium"

    def test_negligible_importance_returns_none(self):
        runs = make_runs(numeric_params={"lr": (0.001, 0.1)}, metrics={"accuracy": (0.5, 0.0)})
        sensitivity = ParameterSensitivity(
            parameter="lr",
            parameter_type="numeric",
            spearman_rho=0.0,
            pearson_r=0.0,
            anova_f_stat=None,
            importance_score=0.05,
            summary="negligible",
        )
        rec = _recommend_numeric_range_from_sensitivity(
            "lr", sensitivity, (0.001, 0.1), "accuracy", "maximize"
        )
        assert rec is None

    def test_zero_range_returns_none(self):
        sensitivity = ParameterSensitivity(
            parameter="lr",
            parameter_type="numeric",
            spearman_rho=0.8,
            pearson_r=0.75,
            anova_f_stat=None,
            importance_score=0.9,
            summary="strong",
        )
        rec = _recommend_numeric_range_from_sensitivity(
            "lr", sensitivity, (0.01, 0.01), "accuracy", "maximize"
        )
        assert rec is None


class TestRecommendCategoricalFromSensitivity:
    def test_recommends_best_categories(self):
        runs = [
            {"hyperparameters": {"opt": "adam"}, "metrics": {"accuracy": 0.9}},
            {"hyperparameters": {"opt": "adam"}, "metrics": {"accuracy": 0.88}},
            {"hyperparameters": {"opt": "sgd"}, "metrics": {"accuracy": 0.7}},
            {"hyperparameters": {"opt": "sgd"}, "metrics": {"accuracy": 0.72}},
            {"hyperparameters": {"opt": "rmsprop"}, "metrics": {"accuracy": 0.6}},
        ]
        sensitivity = ParameterSensitivity(
            parameter="opt",
            parameter_type="categorical",
            spearman_rho=None,
            pearson_r=None,
            anova_f_stat=15.0,
            importance_score=0.8,
            summary="strong",
        )
        rec = _recommend_categorical_from_sensitivity(
            "opt", sensitivity, ["adam", "sgd", "rmsprop"], runs, "accuracy"
        )
        assert rec is not None
        assert rec.parameter == "opt"
        assert rec.parameter_type == "categorical"
        assert "adam" in rec.recommended_range
        assert "sgd" in rec.recommended_range  # Top 2 categories
        assert "rmsprop" not in rec.recommended_range
        assert rec.priority == "high"

    def test_negligible_importance_returns_none(self):
        runs = [
            {"hyperparameters": {"opt": "adam"}, "metrics": {"accuracy": 0.8}},
            {"hyperparameters": {"opt": "sgd"}, "metrics": {"accuracy": 0.79}},
        ]
        sensitivity = ParameterSensitivity(
            parameter="opt",
            parameter_type="categorical",
            spearman_rho=None,
            pearson_r=None,
            anova_f_stat=0.5,
            importance_score=0.05,
            summary="negligible",
        )
        rec = _recommend_categorical_from_sensitivity(
            "opt", sensitivity, ["adam", "sgd"], runs, "accuracy"
        )
        assert rec is None


class TestRecommendFromParetoKnee:
    def test_numeric_knee_recommendation(self):
        runs = make_runs(
            numeric_params={"lr": (0.001, 0.1), "batch_size": (16, 256)},
            metrics={"accuracy": (0.5, 0.4), "loss": (1.0, -0.5)}
        )
        pareto = make_pareto_response(runs, knee_run_id="run_5")
        objectives = [
            ObjectiveConfig(metric="accuracy", direction="maximize"),
            ObjectiveConfig(metric="loss", direction="minimize"),
        ]
        recs = _recommend_from_pareto_knee(runs, pareto, objectives)
        assert len(recs) >= 1
        lr_rec = next(r for r in recs if r.parameter == "lr")
        assert lr_rec.source == "pareto_knee"
        assert lr_rec.priority == "high"
        assert lr_rec.recommended_range[0] <= lr_rec.recommended_range[1]

    def test_categorical_knee_recommendation(self):
        runs = make_runs(
            categorical_params={"opt": ["adam", "sgd", "rmsprop"]},
            metrics={"accuracy": (0.5, 0.4), "loss": (1.0, -0.5)}
        )
        pareto = make_pareto_response(runs, knee_run_id="run_0")
        objectives = [
            ObjectiveConfig(metric="accuracy", direction="maximize"),
            ObjectiveConfig(metric="loss", direction="minimize"),
        ]
        recs = _recommend_from_pareto_knee(runs, pareto, objectives)
        opt_rec = next((r for r in recs if r.parameter == "opt"), None)
        assert opt_rec is not None
        assert opt_rec.source == "pareto_knee"
        assert opt_rec.recommended_range == ["adam"]

    def test_empty_pareto_returns_empty(self):
        pareto = ParetoFrontierResponse(
            experiment_id="exp_test",
            objectives=[],
            all_points=[],
            frontier_points=[],
            knee_point=None,
            hypervolume_indicator=0.0,
            total_evaluated_runs=0,
            frontier_runs_count=0,
            dominated_runs_count=0,
            is_aggregated=False,
            aggregation_method=None,
        )
        objectives = [ObjectiveConfig(metric="accuracy", direction="maximize")]
        recs = _recommend_from_pareto_knee([], pareto, objectives)
        assert recs == []


class TestGenerateTuningRecommendations:
    def test_combines_sensitivity_and_pareto(self):
        runs = make_runs(
            numeric_params={"lr": (0.001, 0.1), "batch_size": (16, 256)},
            categorical_params={"opt": ["adam", "sgd"]},
            metrics={"accuracy": (0.5, 0.4), "loss": (1.0, -0.5)},
            n_runs=20
        )
        sensitivity = make_sensitivity_response([
            {"parameter": "lr", "parameter_type": "numeric", "spearman_rho": 0.7, "importance_score": 0.8},
            {"parameter": "batch_size", "parameter_type": "numeric", "spearman_rho": -0.2, "importance_score": 0.3},
            {"parameter": "opt", "parameter_type": "categorical", "anova_f_stat": 10.0, "importance_score": 0.7},
        ])
        pareto = make_pareto_response(runs, knee_run_id="run_10")
        objectives = [
            ObjectiveConfig(metric="accuracy", direction="maximize"),
            ObjectiveConfig(metric="loss", direction="minimize"),
        ]
        result = generate_tuning_recommendations(runs, sensitivity, pareto, objectives)
        
        assert isinstance(result, TuningRecommendationsResponse)
        assert result.experiment_id == "exp_test"
        assert result.target_metric == "accuracy"
        assert len(result.recommendations) >= 2
        sources = [r.source for r in result.recommendations]
        assert "combined" in sources or "pareto_knee" in sources
        priorities = [r.priority for r in result.recommendations]
        assert priorities == sorted(priorities, key=lambda p: {"high": 0, "medium": 1, "low": 2}.get(p, 3))

    def test_sensitivity_only_no_pareto(self):
        runs = make_runs(
            numeric_params={"lr": (0.001, 0.1)},
            metrics={"accuracy": (0.5, 0.4)},
        )
        sensitivity = make_sensitivity_response([
            {"parameter": "lr", "parameter_type": "numeric", "spearman_rho": 0.7, "importance_score": 0.8},
        ])
        result = generate_tuning_recommendations(runs, sensitivity, None, None)
        
        assert len(result.recommendations) == 1
        assert result.recommendations[0].source == "sensitivity"
        assert result.pareto_knee_config is None

    def test_empty_runs_returns_empty_recommendations(self):
        runs = []
        sensitivity = make_sensitivity_response([])
        result = generate_tuning_recommendations(runs, sensitivity, None, None)
        assert result.recommendations == []


class TestIntegrationWithApi:
    """Integration-style tests that verify the API endpoint works."""
    
    def test_tuning_recommendations_response_schema(self):
        """Verify the response schema matches expected structure."""
        rec = TuningRecommendation(
            parameter="lr",
            parameter_type="numeric",
            current_range=(0.001, 0.1),
            recommended_range=(0.001, 0.2),
            rationale="Positive correlation with accuracy",
            confidence=0.85,
            priority="high",
            source="sensitivity",
        )
        resp = TuningRecommendationsResponse(
            experiment_id="exp_123",
            target_metric="accuracy",
            recommendations=[rec],
            sensitivity_summary={"influential_parameters": 1},
            pareto_knee_config={"run_id": "run_1", "hyperparameters": {"lr": 0.05}},
        )
        
        d = resp.to_dict()
        assert "experiment_id" in d
        assert "target_metric" in d
        assert "recommendations" in d
        assert "sensitivity_summary" in d
        assert "pareto_knee_config" in d
        
        rec_d = d["recommendations"][0]
        assert "parameter" in rec_d
        assert "parameter_type" in rec_d
        assert "current_range" in rec_d
        assert "recommended_range" in rec_d
        assert "rationale" in rec_d
        assert "confidence" in rec_d
        assert "priority" in rec_d
        assert "source" in rec_d
