# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

hyperparameter-tuning-recommendations

## Roadmap

### pareto-frontier-optimization — Multi-Objective Pareto Trade-Off Frontier & Knee-Point Optimization

Status: done

Acceptance:
- Non-dominated sorting algorithm identifies Pareto optimal points across conflicting objectives
- Normalized knee point compromise detected via Euclidean distance to utopia point
- Exact 2D skyline step and Monte Carlo hypervolume indicator calculated
- Interactive SVG chart displays non-dominated curve, knee highlights, and hover inspection

Implementation: `backend/app/services/pareto_engine.py`, `frontend/src/components/ParetoChart.tsx`

Tests: `backend/tests/test_pareto_engine.py`, `frontend/src/__tests__/dashboard.test.tsx`

### cross-seed-hypothesis-testing — Cross-Seed Statistical Significance & Welch's Hypothesis Testing

Status: done

Acceptance:
- Parametric Student's t and non-parametric bootstrap confidence intervals (95% CI)
- Welch's two-sample unequal variance t-test and Mann-Whitney U test against random seed variance
- Effect size quantification with Cohen's d and Cliff's delta
- Statistical power notices alert users when variants have fewer than 3-5 seeds

Implementation: `backend/app/services/statistics_engine.py`, `frontend/src/components/CrossSeedCard.tsx`

Tests: `backend/tests/test_statistics_engine.py`, `backend/tests/test_boundary_conditions.py`

### hyperparameter-sensitivity — Hyperparameter Sensitivity Correlation & Feature Importance

Status: done

Acceptance:
- Spearman rank correlation and Pearson correlation rank parameter influence on target metrics
- ANOVA F-statistic evaluates categorical parameter importance
- Summary annotations describe positive, negative, or negligible parameter relationships

Implementation: `backend/app/services/sensitivity_engine.py`

Tests: `backend/tests/test_boundary_conditions.py`, `backend/tests/test_experiment_workflows.py`

### cryptographic-artifact-registry — Cryptographic Artifact Registry & SHA-256 Tamper Detection

Status: done

Acceptance:
- Model checkpoint and artifact registration with SHA-256 digests
- On-disk checksum calculation and tamper detection
- Audit trail records verification attempts and mismatch notices

Implementation: `backend/app/services/experiment_service.py`, `backend/app/api/artifact_routes.py`, `frontend/src/components/ArtifactRegistry.tsx`

Tests: `backend/tests/test_experiment_workflows.py`

### pairwise-run-diff — Pairwise Run Configuration & Metric Diff Analyzer

Status: done

Acceptance:
- Side-by-side comparison of hyperparameters and evaluation metrics
- Absolute and percentage delta calculation with direction-aware improvement badges

Implementation: `backend/app/services/experiment_service.py`, `frontend/src/components/RunDiffModal.tsx`

Tests: `backend/tests/test_experiment_workflows.py`

### bundle-export-import — Experiment Bundle Export/Import & Tabular CSV/Markdown Reporting

Status: done

Acceptance:
- Downloadable CSV export of runs and metrics with optional variant filter
- Reproducible JSON bundle export and multi-run import
- Markdown evaluation report generation with table and artifact list

Implementation: `backend/app/api/export_routes.py`

Tests: `backend/tests/test_experiment_workflows.py`

### grounded-advisory-synthesis — Grounded LLM Advisory Synthesis with Deterministic Offline Fallback

Status: done

Acceptance:
- Evidence-grounded trade-off explanations referencing calculated Pareto and Welch stats
- Offline deterministic fallback produces actionable advice without API credentials
- Multi-provider adapter support (OpenAI, Anthropic, Gemini, Ollama) with credential redaction

Implementation: `backend/app/services/llm_service.py`

Tests: `backend/tests/test_llm_advisory.py`

### oidc-rbac-security — OIDC Keycloak Authentication, RBAC Tiers & CSRF Protection

Status: done

Acceptance:
- OIDC authorization-code flow with PKCE, state, and nonce validation
- Role-Based Access Control enforcing admin, analyst, and viewer roles
- HMAC double-submit CSRF protection on mutating HTTP requests

Implementation: `backend/app/core/auth.py`, `backend/app/api/auth_routes.py`

Tests: `backend/tests/test_auth.py`, `backend/tests/test_http_boundary.py`

### variant-aggregated-pareto — Multi-Seed Variant-Aggregated Pareto Trade-Off Optimization

Status: done

Acceptance:
- Pareto analysis API supports aggregate_by_variant flag and aggregation_method ('mean' or 'median')
- Multi-seed runs for each variant are grouped and aggregated into representative variant points
- Non-dominated sorting, knee point detection, and hypervolume calculation operate over variant representatives
- Aggregated Pareto points preserve sample size N and evaluated seed list metadata
- Frontend provides an interactive toggle in Pareto chart controls to switch between raw runs and aggregated variants
- Pareto chart displays variant aggregation badge and sample size details in inspection tooltips

Implementation: `backend/app/services/pareto_engine.py`, `backend/app/models/schemas.py`, `backend/app/api/analysis_routes.py`, `frontend/src/types/index.ts`, `frontend/src/api/client.ts`, `frontend/src/components/ParetoChart.tsx`, `frontend/src/App.tsx`

Tests: `backend/tests/test_pareto_engine.py`, `backend/tests/test_experiment_workflows.py`, `frontend/src/__tests__/dashboard.test.tsx`

### hyperparameter-tuning-recommendations — Automated Hyperparameter Tuning Recommendations

Status: in_progress

Acceptance:
- Search interval recommendations for influential hyperparameters identified in sensitivity analysis
- Boundary suggestions based on knee point parameter configurations
- Integration with existing sensitivity and Pareto engines
- API endpoint for retrieving tuning recommendations
- Frontend display of recommendations in sensitivity analysis tab

Implementation: `backend/app/services/tuning_engine.py`, `backend/app/api/tuning_routes.py`, `frontend/src/components/TuningRecommendations.tsx`

Tests: `backend/tests/test_tuning_engine.py`, `frontend/src/__tests__/tuning.test.tsx`

