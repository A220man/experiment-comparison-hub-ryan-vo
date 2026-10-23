import datetime as dt
from typing import Any, Dict as D, List as L, Literal, Optional as O
from pydantic import BaseModel as B, ConfigDict, field_validator
F = float; S = str; I = int; OF = O[F]; OS = O[S]; OI = O[I]
_orm = ConfigDict(from_attributes=True)

class PaginatedResponse(B): total: I; page: I; page_size: I; pages: I
class UserResponse(B): user_id: S; email: S; name: S; roles: L[S]; session_id: S; is_demo: bool
class DemoSwitchRequest(B): profile: Literal['admin', 'analyst', 'viewer']
class ExperimentCreate(B): name: S; description: OS = None; domain: S = 'ai-ml'; baseline_variant: OS = None
class ExperimentUpdate(B): name: OS = None; description: OS = None; baseline_variant: OS = None
class ExperimentResponse(B):
    model_config = _orm
    id: S; name: S; description: OS; domain: S; baseline_variant: OS; created_by: S; created_at: dt.datetime; updated_at: dt.datetime; run_count: OI = 0
class ExperimentListResponse(PaginatedResponse): items: L[ExperimentResponse]

class RunCreate(B):
    experiment_id: S; name: S; variant_name: S; seed: I = 42; hyperparameters: D[S, Any] = {}; metrics: D[S, F] = {}; status: S = 'COMPLETED'; commit_hash: OS = None; tags: L[S] = []; notes: OS = None
    @field_validator('metrics')
    @classmethod
    def validate_metrics_numeric(cls, v: D[S, Any]) -> D[S, F]:
        try: return {k: F(val) for k, val in v.items()}
        except (ValueError, TypeError) as e: raise ValueError(f"Metric must be float: {e}")

class RunBatchCreate(B): experiment_id: S; runs: L[RunCreate]
class RunUpdate(B): name: OS = None; tags: O[L[S]] = None; notes: OS = None; status: OS = None; metrics: O[D[S, F]] = None
class RunResponse(B):
    model_config = _orm
    id: S; experiment_id: S; name: S; variant_name: S; seed: I; hyperparameters: D[S, Any]; metrics: D[S, F]; status: S; commit_hash: OS; tags: L[S]; notes: OS; created_by: S; created_at: dt.datetime
class RunListResponse(PaginatedResponse): items: L[RunResponse]

class ArtifactCreate(B): run_id: S; name: S; artifact_type: S; file_path: S; file_size_bytes: I = 0; sha256_hash: S; metadata_json: D[S, Any] = {}
class ArtifactResponse(B):
    model_config = _orm
    id: S; run_id: S; name: S; artifact_type: S; file_path: S; file_size_bytes: I; sha256_hash: S; verified: bool; metadata_json: D[S, Any]; created_at: dt.datetime
class ArtifactVerifyResponse(B): artifact_id: S; name: S; expected_sha256: S; actual_sha256: OS; verified: bool; message: S

class ParameterDelta(B): parameter: S; base_value: Any; target_value: Any; changed: bool
class MetricDelta(B): metric: S; base_value: OF; target_value: OF; absolute_delta: OF; percent_change: OF; improved: O[bool]
class RunDiffResponse(B): base_run: RunResponse; target_run: RunResponse; parameter_deltas: L[ParameterDelta]; metric_deltas: L[MetricDelta]
class ObjectiveConfig(B): metric: S; direction: Literal['maximize', 'minimize']

class ParetoRequest(B): experiment_id: S; objectives: L[ObjectiveConfig]; variant_filter: O[L[S]] = None; seed_filter: O[L[I]] = None; aggregate_by_variant: bool = False; aggregation_method: Literal['mean', 'median'] = 'mean'
class ParetoPoint(B): run_id: S; run_name: S; variant_name: S; seed: I; metrics: D[S, F]; is_frontier: bool; is_knee_point: bool; normalized_distance_to_utopia: OF = None; sample_size_n: OI = None; seeds: O[L[I]] = None
class ParetoFrontierResponse(B): experiment_id: S; objectives: L[ObjectiveConfig]; all_points: L[ParetoPoint]; frontier_points: L[ParetoPoint]; knee_point: O[ParetoPoint]; hypervolume_indicator: F; total_evaluated_runs: I; frontier_runs_count: I; dominated_runs_count: I; is_aggregated: bool = False; aggregation_method: OS = None

class CrossSeedRequest(B): experiment_id: S; baseline_variant: OS = None; metrics: L[S] = ['accuracy', 'val_loss', 'latency_ms']; alpha: F = 0.05
class ConfidenceInterval(B): lower: F; upper: F; confidence_level: F = 0.95; method: S
class SeedAggregatedMetric(B): variant_name: S; metric: S; sample_size_n: I; mean: F; std_dev: F; median: F; iqr: F; min_value: F; max_value: F; standard_error: F; ci_t_distribution: ConfidenceInterval; ci_bootstrap: ConfidenceInterval; seeds: L[I]
class HypothesisTestResult(B): baseline_variant: S; treatment_variant: S; metric: S; baseline_mean: F; treatment_mean: F; mean_delta: F; percent_change: F; t_statistic: F; p_value_welch: F; p_value_mann_whitney: F; cohens_d: F; cliffs_delta: F; is_statistically_significant: bool; significance_label: S; conclusion: S
class CrossSeedResponse(B): experiment_id: S; baseline_variant: S; variants_evaluated: L[S]; metrics_evaluated: L[S]; aggregations: L[SeedAggregatedMetric]; hypothesis_tests: L[HypothesisTestResult]; sample_size_warnings: L[S]

class SensitivityRequest(B): experiment_id: S; target_metric: S = 'accuracy'
class ParameterSensitivity(B): parameter: S; parameter_type: Literal['numeric', 'categorical']; pearson_r: OF = None; spearman_rho: OF = None; importance_score: F; summary: S
class SensitivityResponse(B): experiment_id: S; target_metric: S; total_runs_analyzed: I; parameters: L[ParameterSensitivity]

class LeaderboardEntry(B): rank: I; variant_name: S; composite_score: F; pareto_score: F; significance_score: F; is_frontier: bool; is_knee_point: bool; is_baseline: bool; metrics: D[S, F]; sample_size_n: I; seeds: L[I]; avg_welch_p_value: F; avg_cohens_d: F; hypervolume_contribution: F
class LeaderboardRequest(B): experiment_id: S; objectives: L[ObjectiveConfig]; baseline_variant: OS = None; variant_filter: O[L[S]] = None; seed_filter: O[L[I]] = None; aggregate_by_variant: bool = True; aggregation_method: Literal['mean', 'median'] = 'mean'; weight_pareto: F = 0.5; weight_significance: F = 0.5
class LeaderboardResponse(B): experiment_id: S; objectives: L[ObjectiveConfig]; baseline_variant: S; leaderboard: L[LeaderboardEntry]; total_variants: I; weight_pareto: F; weight_significance: F; aggregation_method: OS = None; is_aggregated: bool = False

class AdvisoryExplanationRequest(B): experiment_id: S; analysis_type: Literal['pareto', 'cross_seed', 'comprehensive'] = 'comprehensive'
class AdvisoryExplanationResponse(B): experiment_id: S; provider: S; model: S; is_advisory: bool = True; disclaimer: S; offline_fallback: bool; advisory_text: S; evidence_summary: D[S, Any]

class AuditLogResponse(B):
    model_config = _orm
class TuningRecommendation(B):
    parameter: S
    parameter_type: Literal['numeric', 'categorical']
    current_range: L[Any]
    recommended_range: L[Any]
    rationale: S
    confidence: F
    priority: Literal['high', 'medium', 'low']
    source: Literal['sensitivity', 'pareto_knee', 'combined']

class TuningRecommendationsResponse(B):
    experiment_id: S
    target_metric: S
    recommendations: L[TuningRecommendation]
    sensitivity_summary: D[S, Any]
    pareto_knee_config: O[D[S, Any]] = None
class AuditLogListResponse(PaginatedResponse): items: L[AuditLogResponse]
