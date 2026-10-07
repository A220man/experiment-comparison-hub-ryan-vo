# Changelog

## [1.3.0] - 2026-10-07

## [1.2.0] - 2026-10-07

## [1.1.0] - 2026-10-07

## Unreleased

- Add CSV export endpoint (`GET /api/v1/export/runs.csv`) for tabular metrics and hyperparameter export with optional variant filtering.
- Support generalized metric optimization direction detection across loss, latency, error, perplexity, memory, and cost metrics.
- Add experiment bundle import workflow in the frontend with file upload and JSON editor.
- Add run detail inspection modal in frontend accessible from run table rows and Pareto chart points.
- Fix hypothesis test outcome badge logic in `CrossSeedCard` to accurately differentiate significant gains, degradations, and inconclusive seed variance.
- Fix backend CI package imports by running pytest from the repository root.
- Fix the backend Docker build context and missing target package directory.
- Exclude local dependencies and runtime data from the Docker build context.
- Run real backend and frontend container health smoke checks in CI.

## [1.0.0] - 2026-10-07

All notable changes to the Experiment Comparison Hub will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-07

### Added
- **Multi-Objective Pareto Trade-Off Optimization**:
  - Non-dominated sorting algorithm to calculate the Pareto frontier across conflicting objectives (e.g., accuracy vs. latency, throughput vs. memory).
  - Normalized knee point compromise detection minimizing Euclidean distance to the ideal utopia vector.
  - Hypervolume indicator calculation (exact step-wise 2D skyline and Monte Carlo integration for higher dimensions).
  - Interactive SVG Pareto frontier chart with real-time hover inspection, skyline curves, and knee point highlights.

- **Cross-Seed Statistical Significance & Hypothesis Testing**:
  - Multi-seed metric aggregation including parametric (mean, standard deviation, standard error) and non-parametric statistics (median, IQR).
  - Dual 95% confidence intervals: Student's t-distribution for small sample sizes and percentile empirical bootstrap resampling.
  - Welch's two-sample t-test (two-tailed, unequal variance) and Mann-Whitney U rank-sum test against random seed variance.
  - Effect size quantification via Cohen's d (pooled standard deviation) and Cliff's delta non-parametric delta.
  - Statistical power notices alerting users when seed counts (N < 3–5) are underpowered.

- **Hyperparameter Sensitivity & Cryptographic Artifact Registry**:
  - Parameter importance ranking evaluated via Spearman rank correlation and Pearson correlation against target metrics.
  - SHA-256 cryptographic checksum calculation and integrity verification for model checkpoints and evaluation artifacts.
  - Pairwise run diff analyzer comparing configuration parameters and metric divergence side-by-side.

- **Opt-In Grounded Advisory Explanation**:
  - Domain advisory synthesis strictly grounded in calculated empirical evidence (Pareto knee points, Welch's t-test p-values, and effect sizes).
  - Deterministic offline fallback engine operating without external API credentials.
  - External adapter support for OpenAI-compatible endpoints, Anthropic Messages API, Gemini generateContent REST, and Ollama.
  - Redaction of sensitive credentials and bounded network timeouts.

- **Authentication & Security Infrastructure**:
  - OpenID Connect (OIDC) authorization-code flow with PKCE, state, and nonce validation via Keycloak.
  - Cryptographically signed HttpOnly SameSite session cookies with double-submit CSRF protection on mutation routes.
  - Role-Based Access Control (RBAC) enforcing `admin`, `analyst`, and `viewer` tiers across all endpoints.
  - Explicit local demo mode persona switching refused at startup in production environments.
  - Immutable audit trail recording mutations, actors, timestamps, and network origins.

- **Deployment & Developer Tooling**:
  - Multi-stage Dockerfiles with non-root runtime users for backend and frontend.
  - `compose.yaml` orchestrating backend, frontend, and Keycloak with persistent volumes and healthchecks.
  - Automated CI workflow validating backend pytest suites, frontend Vitest tests, typechecking, Vite production builds, and container builds.
