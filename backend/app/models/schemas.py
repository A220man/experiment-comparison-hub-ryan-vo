import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, field_validator
_orm = ConfigDict(from_attributes=True)

class PaginatedResponse(BaseModel):
    total: int; page: int; page_size: int; pages: int

class UserResponse(BaseModel):
    user_id: str; email: str; name: str; roles: List[str]; session_id: str; is_demo: bool

class DemoSwitchRequest(BaseModel):
    profile: Literal['admin', 'analyst', 'viewer']

class ExperimentCreate(BaseModel):
    name: str; description: Optional[str] = None; domain: str = 'ai-ml'; baseline_variant: Optional[str] = None

class ExperimentUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None; baseline_variant: Optional[str] = None

class ExperimentResponse(BaseModel):
    model_config = _orm
    id: str; name: str; description: Optional[str]; domain: str; baseline_variant: Optional[str]; created_by: str; created_at: datetime.datetime; updated_at: datetime.datetime; run_count: Optional[int] = 0

class ExperimentListResponse(PaginatedResponse):
    items: List[ExperimentResponse]

class RunCreate(BaseModel):
    experiment_id: str; name: str; variant_name: str; seed: int = 42; hyperparameters: Dict[str, Any] = {}; metrics: Dict[str, float] = {}; status: str = 'COMPLETED'; commit_hash: Optional[str] = None; tags: List[str] = []; notes: Optional[str] = None

    @field_validator('metrics')
    @classmethod
    def validate_metrics_numeric(cls, v: Dict[str, Any]) -> Dict[str, float]:
        try: return {k: float(val) for k, val in v.items()}
        except (ValueError, TypeError) as e: raise ValueError(f"Metric must be float: {e}")

class RunBatchCreate(BaseModel):
    experiment_id: str; runs: List[RunCreate]

class RunUpdate(BaseModel):
    name: Optional[str] = None; tags: Optional[List[str]] = None; notes: Optional[str] = None; status: Optional[str] = None; metrics: Optional[Dict[str, float]] = None

class RunResponse(BaseModel):
    model_config = _orm
    id: str; experiment_id: str; name: str; variant_name: str; seed: int; hyperparameters: Dict[str, Any]; metrics: Dict[str, float]; status: str; commit_hash: Optional[str]; tags: List[str]; notes: Optional[str]; created_by: str; created_at: datetime.datetime

class RunListResponse(PaginatedResponse):
    items: List[RunResponse]

class ArtifactCreate(BaseModel):
    run_id: str; name: str; artifact_type: str; file_path: str; file_size_bytes: int = 0; sha256_hash: str; metadata_json: Dict[str, Any] = {}

class ArtifactResponse(BaseModel):
    model_config = _orm
    id: str; run_id: str; name: str; artifact_type: str; file_path: str; file_size_bytes: int; sha256_hash: str; verified: bool; metadata_json: Dict[str, Any]; created_at: datetime.datetime

class ArtifactVerifyResponse(BaseModel):
    artifact_id: str; name: str; expected_sha256: str; actual_sha256: Optional[str]; verified: bool; message: str

class ParameterDelta(BaseModel):
    parameter: str; base_value: Any; target_value: Any; changed: bool

class MetricDelta(BaseModel):
    metric: str; base_value: Optional[float]; target_value: Optional[float]; absolute_delta: Optional[float]; percent_change: Optional[float]; improved: Optional[bool]

class RunDiffResponse(BaseModel):
    base_run: RunResponse; target_run: RunResponse; parameter_deltas: List[ParameterDelta]; metric_deltas: List[MetricDelta]

class ObjectiveConfig(BaseModel):
    metric: str; direction: Literal['maximize', 'minimize']

class ParetoRequest(BaseModel):
    experiment_id: str; objectives: List[ObjectiveConfig]; variant_filter: Optional[List[str]] = None

class ParetoPoint(BaseModel):
    run_id: str; run_name: str; variant_name: str; seed: int; metrics: Dict[str, float]; is_frontier: bool; is_knee_point: bool; normalized_distance_to_utopia: Optional[float] = None

class ParetoFrontierResponse(BaseModel):
    experiment_id: str; objectives: List[ObjectiveConfig]; all_points: List[ParetoPoint]; frontier_points: List[ParetoPoint]; knee_point: Optional[ParetoPoint]; hypervolume_indicator: float; total_evaluated_runs: int; frontier_runs_count: int; dominated_runs_count: int

class CrossSeedRequest(BaseModel):
    experiment_id: str; baseline_variant: Optional[str] = None; metrics: List[str] = ['accuracy', 'val_loss', 'latency_ms']; alpha: float = 0.05

class ConfidenceInterval(BaseModel):
    lower: float; upper: float; confidence_level: float = 0.95; method: str

class SeedAggregatedMetric(BaseModel):
    variant_name: str; metric: str; sample_size_n: int; mean: float; std_dev: float; median: float; iqr: float; min_value: float; max_value: float; standard_error: float; ci_t_distribution: ConfidenceInterval; ci_bootstrap: ConfidenceInterval; seeds: List[int]

class HypothesisTestResult(BaseModel):
    baseline_variant: str; treatment_variant: str; metric: str; baseline_mean: float; treatment_mean: float; mean_delta: float; percent_change: float; t_statistic: float; p_value_welch: float; p_value_mann_whitney: float; cohens_d: float; cliffs_delta: float; is_statistically_significant: bool; significance_label: str; conclusion: str

class CrossSeedResponse(BaseModel):
    experiment_id: str; baseline_variant: str; variants_evaluated: List[str]; metrics_evaluated: List[str]; aggregations: List[SeedAggregatedMetric]; hypothesis_tests: List[HypothesisTestResult]; sample_size_warnings: List[str]

class SensitivityRequest(BaseModel):
    experiment_id: str; target_metric: str = 'accuracy'

class ParameterSensitivity(BaseModel):
    parameter: str; parameter_type: Literal['numeric', 'categorical']; pearson_r: Optional[float] = None; spearman_rho: Optional[float] = None; importance_score: float; summary: str

class SensitivityResponse(BaseModel):
    experiment_id: str; target_metric: str; total_runs_analyzed: int; parameters: List[ParameterSensitivity]

class AdvisoryExplanationRequest(BaseModel):
    experiment_id: str; analysis_type: Literal['pareto', 'cross_seed', 'comprehensive'] = 'comprehensive'

class AdvisoryExplanationResponse(BaseModel):
    experiment_id: str; provider: str; model: str; is_advisory: bool = True; disclaimer: str; offline_fallback: bool; advisory_text: str; evidence_summary: Dict[str, Any]

class AuditLogResponse(BaseModel):
    model_config = _orm
    id: str; user_email: str; action: str; resource_type: str; resource_id: str; details_json: Dict[str, Any]; ip_address: Optional[str]; timestamp: datetime.datetime

class AuditLogListResponse(PaginatedResponse):
    items: List[AuditLogResponse]
