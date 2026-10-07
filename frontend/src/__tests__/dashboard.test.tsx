import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Navbar } from "../components/Navbar";
import { ParetoChart } from "../components/ParetoChart";
import { CrossSeedCard } from "../components/CrossSeedCard";
import { ArtifactRegistry } from "../components/ArtifactRegistry";
import { AuthProvider } from "../context/AuthContext";
import { ParetoFrontierResult, CrossSeedResult, Artifact } from "../types";

vi.mock("../api/client", () => {
  return {
    setCsrfToken: vi.fn(),
    api: {
      auth: {
        getMe: vi.fn().mockResolvedValue({
          user_id: "usr-demo-analyst",
          email: "ryandtvo@gmail.com",
          name: "Ryan Vo",
          roles: ["analyst"],
          session_id: "sess-123",
          is_demo: true,
        }),
        fetchCsrfToken: vi.fn().mockResolvedValue("test-csrf"),
        logout: vi.fn().mockResolvedValue({ status: "ok" }),
        demoSwitch: vi.fn().mockResolvedValue({
          status: "ok",
          user: {
            user_id: "usr-demo-admin",
            email: "ryandtvo@gmail.com",
            name: "Ryan Vo",
            roles: ["admin"],
            session_id: "sess-123",
            is_demo: true,
          },
          csrf_token: "test-csrf",
        }),
      },
      artifacts: {
        verify: vi.fn().mockResolvedValue({
          artifact_id: "art-1",
          name: "checkpoint.pt",
          expected_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          actual_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          verified: true,
          message: "Cryptographic hash verified successfully",
        }),
      },
    },
  };
});

describe("Experiment Comparison Hub Frontend", () => {
  it("renders Navbar with Ryan Vo author attribution and user roles", async () => {
    render(
      <AuthProvider>
        <Navbar />
      </AuthProvider>
    );

    expect(screen.getByText("Experiment Comparison Hub")).toBeInTheDocument();
    expect(screen.getByText("Ryan Vo | AI & Machine Learning")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Ryan Vo")).toBeInTheDocument();
      expect(screen.getByText("ryandtvo@gmail.com")).toBeInTheDocument();
    });
  });

  it("renders ParetoChart with non-dominated trade-off skyline and hypervolume indicator", () => {
    const mockParetoData: ParetoFrontierResult = {
      experiment_id: "exp-1",
      objectives: [
        { metric: "accuracy", direction: "maximize" },
        { metric: "latency_ms", direction: "minimize" },
      ],
      all_points: [
        {
          run_id: "run-1",
          run_name: "Dense Baseline",
          variant_name: "dense",
          seed: 42,
          metrics: { accuracy: 0.85, latency_ms: 20.0 },
          is_frontier: true,
          is_knee_point: false,
          normalized_distance_to_utopia: 0.35,
        },
        {
          run_id: "run-2",
          run_name: "Pruned 30%",
          variant_name: "pruned",
          seed: 42,
          metrics: { accuracy: 0.84, latency_ms: 12.0 },
          is_frontier: true,
          is_knee_point: true,
          normalized_distance_to_utopia: 0.15,
        },
      ],
      frontier_points: [
        {
          run_id: "run-2",
          run_name: "Pruned 30%",
          variant_name: "pruned",
          seed: 42,
          metrics: { accuracy: 0.84, latency_ms: 12.0 },
          is_frontier: true,
          is_knee_point: true,
          normalized_distance_to_utopia: 0.15,
        },
      ],
      knee_point: {
        run_id: "run-2",
        run_name: "Pruned 30%",
        variant_name: "pruned",
        seed: 42,
        metrics: { accuracy: 0.84, latency_ms: 12.0 },
        is_frontier: true,
        is_knee_point: true,
        normalized_distance_to_utopia: 0.15,
      },
      hypervolume_indicator: 0.7854,
      total_evaluated_runs: 2,
      frontier_runs_count: 1,
      dominated_runs_count: 1,
    };

    render(<ParetoChart data={mockParetoData} />);

    expect(screen.getByText("Multi-Objective Pareto Trade-Off Frontier")).toBeInTheDocument();
    expect(screen.getByText("Non-Dominated Skyline")).toBeInTheDocument();
    expect(screen.getByText("0.7854")).toBeInTheDocument();
    expect(screen.getByText("Knee: pruned")).toBeInTheDocument();
  });

  it("renders CrossSeedCard with Welch's t-test significance and power warnings", () => {
    const mockCrossSeed: CrossSeedResult = {
      experiment_id: "exp-1",
      baseline_variant: "dense",
      variants_evaluated: ["dense", "pruned"],
      metrics_evaluated: ["accuracy"],
      sample_size_warnings: [
        "Variant 'pruned' has N=3 runs. Minimum N>=5 recommended for robust statistical power.",
      ],
      aggregations: [
        {
          variant_name: "pruned",
          metric: "accuracy",
          sample_size_n: 3,
          mean: 0.842,
          std_dev: 0.005,
          median: 0.841,
          iqr: 0.008,
          min_value: 0.837,
          max_value: 0.848,
          standard_error: 0.003,
          ci_t_distribution: { lower: 0.835, upper: 0.849, confidence_level: 0.95, method: "student_t" },
          ci_bootstrap: { lower: 0.838, upper: 0.846, confidence_level: 0.95, method: "bootstrap" },
          seeds: [1, 2, 3],
        },
      ],
      hypothesis_tests: [
        {
          treatment_variant: "pruned",
          baseline_variant: "dense",
          metric: "accuracy",
          baseline_mean: 0.820,
          treatment_mean: 0.842,
          mean_delta: 0.022,
          percent_change: 2.68,
          t_statistic: 4.12,
          p_value_welch: 0.0145,
          p_value_mann_whitney: 0.02,
          cohens_d: 2.38,
          cliffs_delta: 1.0,
          is_statistically_significant: true,
          significance_label: "Statistically Significant Improvement",
          conclusion: "Reject H0 (p=0.0145 < 0.05). Verified improvement.",
        },
      ],
    };

    render(<CrossSeedCard data={mockCrossSeed} />);

    expect(screen.getByText(/Welch's Two-Sample t-Test/i)).toBeInTheDocument();
    expect(screen.getByText("Statistical Power Notice:")).toBeInTheDocument();
    expect(screen.getByText(/Significant Gain/i)).toBeInTheDocument();
    expect(screen.getByText("0.0145")).toBeInTheDocument();
  });

  it("renders ArtifactRegistry and triggers cryptographic SHA-256 integrity verification", async () => {
    const mockArtifacts: Artifact[] = [
      {
        id: "art-1",
        run_id: "run-1",
        name: "model_weights.pt",
        artifact_type: "model_checkpoint",
        file_path: "/data/checkpoints/model_weights.pt",
        file_size_bytes: 52428800,
        sha256_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        verified: false,
        metadata_json: {},
        created_at: "2026-10-07T00:00:00Z",
      },
    ];

    const onRefresh = vi.fn();

    render(
      <AuthProvider>
        <ArtifactRegistry artifacts={mockArtifacts} runId="run-1" onRefresh={onRefresh} />
      </AuthProvider>
    );

    expect(screen.getByText("model_weights.pt")).toBeInTheDocument();
    expect(screen.getByText("50 MB")).toBeInTheDocument();

    const verifyBtn = screen.getByRole("button", { name: /Verify Checksum/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalled();
    });
  });
});
