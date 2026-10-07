export interface UserProfile {
  user_id: string; email: string; name: string; roles: string[]; session_id: string; is_demo: boolean;
}
export interface Experiment {
  id: string; name: string; description?: string; domain: string; baseline_variant?: string; created_by: string; created_at: string; updated_at: string; run_count?: number;
}
export interface Run {
  id: string; experiment_id: string; name: string; variant_name: string; seed: number; hyperparameters: Record<string, any>; metrics: Record<string, number>; status: string; commit_hash?: string; tags: string[]; notes?: string; created_by: string; created_at: string;
}
export interface Artifact {
  id: string; run_id: string; name: string; artifact_type: string; file_path: string; file_size_bytes: number; sha256_hash: string; verified: boolean; metadata_json: Record<string, any>; created_at: string;
}
export interface ArtifactVerifyResult {
  artifact_id: string; name: string; expected_sha256: string; actual_sha256: string | null; verified: boolean; message: string;
}
export interface ParameterDelta {
  parameter: string; base_value: any; target_value: any; changed: boolean;
}
export interface MetricDelta {
  metric: string; base_value: number | null; target_value: number | null; absolute_delta: number | null; percent_change: number | null; improved: boolean | null;
}
export interface RunDiffResult {
  base_run: Run; target_run: Run; parameter_deltas: ParameterDelta[]; metric_deltas: MetricDelta[];
}
export interface ObjectiveConfig {
  metric: string; direction: "maximize" | "minimize";
}
export interface ParetoPoint {
  run_id: string; run_name: string; variant_name: string; seed: number; metrics: Record<string, number>; is_frontier: boolean; is_knee_point: boolean; normalized_distance_to_utopia: number | null;
}
export interface ParetoFrontierResult {
  experiment_id: string; objectives: ObjectiveConfig[]; all_points: ParetoPoint[]; frontier_points: ParetoPoint[]; knee_point: ParetoPoint | null; hypervolume_indicator: number; total_evaluated_runs: number; frontier_runs_count: number; dominated_runs_count: number;
}
export interface ConfidenceInterval {
  lower: number; upper: number; confidence_level: number; method: string;
}
export interface SeedAggregatedMetric {
  variant_name: string; metric: string; sample_size_n: number; mean: number; std_dev: number; median: number; iqr: number; min_value: number; max_value: number; standard_error: number; ci_t_distribution: ConfidenceInterval; ci_bootstrap: ConfidenceInterval; seeds: number[];
}
export interface HypothesisTestResult {
  baseline_variant: string; treatment_variant: string; metric: string; baseline_mean: number; treatment_mean: number; mean_delta: number; percent_change: number; t_statistic: number; p_value_welch: number; p_value_mann_whitney: number; cohens_d: number; cliffs_delta: number; is_statistically_significant: boolean; significance_label: string; conclusion: string;
}
export interface CrossSeedResult {
  experiment_id: string; baseline_variant: string; variants_evaluated: string[]; metrics_evaluated: string[]; aggregations: SeedAggregatedMetric[]; hypothesis_tests: HypothesisTestResult[]; sample_size_warnings: string[];
}
export interface ParameterSensitivity {
  parameter: string; parameter_type: "numeric" | "categorical"; pearson_r: number | null; spearman_rho: number | null; importance_score: number; summary: string;
}
export interface SensitivityResult {
  experiment_id: string; target_metric: string; total_runs_analyzed: number; parameters: ParameterSensitivity[];
}
export interface AdvisoryExplanationResult {
  experiment_id: string; provider: string; model: string; is_advisory: boolean; disclaimer: string; offline_fallback: boolean; advisory_text: string; evidence_summary: Record<string, any>;
}
export interface AuditLogItem {
  id: string; user_email: string; action: string; resource_type: string; resource_id: string; details_json: Record<string, any>; ip_address: string | null; timestamp: string;
}
