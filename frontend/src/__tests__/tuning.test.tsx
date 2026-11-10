import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TuningRecommendations } from "../components/TuningRecommendations";
import { AuthProvider } from "../context/AuthContext";
import { TuningRecommendationsResponse } from "../types";

vi.mock("../api/client", () => {
  return {
    setCsrfToken: vi.fn(),
    api: {
      getTuningRecommendations: vi.fn(),
      getExperiments: vi.fn().mockResolvedValue([]),
      getRuns: vi.fn().mockResolvedValue([]),
    },
  };
});

const mockTuningData: TuningRecommendationsResponse = {
  experiment_id: "exp_123",
  target_metric: "accuracy",
  recommendations: [
    {
      parameter: "learning_rate",
      parameter_type: "numeric",
      current_range: [0.001, 0.1],
      recommended_range: [0.001, 0.2],
      rationale: "Strong positive Spearman correlation (ρ=0.750) with accuracy. Increasing learning_rate tends to improve performance.",
      confidence: 0.85,
      priority: "high",
      source: "sensitivity",
    },
    {
      parameter: "batch_size",
      parameter_type: "numeric",
      current_range: [16, 256],
      recommended_range: [16, 512],
      rationale: "Moderate correlation (ρ=-0.150) with accuracy. Optimum may lie outside observed range; expanding search bounds.",
      confidence: 0.55,
      priority: "medium",
      source: "sensitivity",
    },
    {
      parameter: "optimizer",
      parameter_type: "categorical",
      current_range: ["adam", "sgd", "rmsprop"],
      recommended_range: ["adam", "sgd"],
      rationale: "ANOVA indicates categorical parameter 'optimizer' significantly affects accuracy (F-statistic implied importance=0.800). Best observed category: 'adam' (mean=0.9200) vs worst: 'rmsprop' (mean=0.7500). Consider focusing search on top-performing categories.",
      confidence: 0.78,
      priority: "high",
      source: "pareto_knee",
    },
    {
      parameter: "weight_decay",
      parameter_type: "numeric",
      current_range: [1e-5, 1e-3],
      recommended_range: [1e-5, 5e-4],
      rationale: "Pareto knee point configuration uses weight_decay=0.0005. This represents the optimal trade-off across objectives ['accuracy (maximize)', 'loss (minimize)']. Consider focusing search near this value. Additionally, Strong negative Spearman correlation (ρ=-0.650) with accuracy. Decreasing weight_decay tends to improve performance.",
      confidence: 0.9,
      priority: "high",
      source: "combined",
    },
  ],
  sensitivity_summary: {
    total_parameters_analyzed: 4,
    influential_parameters: 4,
    top_parameters: [
      { parameter: "learning_rate", importance: 0.9, type: "numeric" },
      { parameter: "optimizer", importance: 0.8, type: "categorical" },
      { parameter: "weight_decay", importance: 0.7, type: "numeric" },
      { parameter: "batch_size", importance: 0.3, type: "numeric" },
    ],
  },
  pareto_knee_config: {
    run_id: "run_5",
    run_name: "pruned_run",
    variant_name: "base_config",
    hyperparameters: { learning_rate: 0.05, batch_size: 128, optimizer: "adam", weight_decay: 0.0005 },
    metrics: { accuracy: 0.95, loss: 0.12 },
    normalized_distance_to_utopia: 0.085,
  },
};

const defaultProps = {
  data: mockTuningData,
  onRefresh: vi.fn(),
  availableMetrics: ["accuracy", "loss", "f1_score", "precision", "recall"],
};

describe("TuningRecommendations Component", () => {
  it("renders the tuning recommendations panel with title", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByText("Hyperparameter Tuning Recommendations")).toBeInTheDocument();
    expect(screen.getByText(/Target metric:/)).toBeInTheDocument();
    expect(screen.getByText("accuracy")).toBeInTheDocument();
  });

  it("displays sensitivity summary with parameter counts", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );
    expect(screen.getByText("Sensitivity Summary")).toBeInTheDocument();
    expect(screen.getByText(/total_parameters_analyzed: 4\.000/)).toBeInTheDocument();
    expect(screen.getByText(/influential_parameters: 4\.000/)).toBeInTheDocument();
  });

  it("renders Pareto knee point configuration badge", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByText("Pareto Knee Point Configuration")).toBeInTheDocument();
    expect(screen.getByText(/run_id: run_5/)).toBeInTheDocument();
    expect(screen.getByText(/run_name: pruned_run/)).toBeInTheDocument();
    expect(screen.getByText(/variant_name: base_config/)).toBeInTheDocument();
    expect(screen.getByText(/normalized_distance_to_utopia: 0\.085/)).toBeInTheDocument();
  });

  it("displays all recommendations with correct priority badges", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    const highPriorityBadges = screen.getAllByText("High");
    expect(highPriorityBadges.length).toBe(3);
    expect(screen.getByText("Medium")).toBeInTheDocument();
  });

  it("shows source badges for each recommendation", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByText("Sensitivity Analysis")).toBeInTheDocument();
    expect(screen.getByText("Pareto Knee Point")).toBeInTheDocument();
    expect(screen.getByText("Combined Evidence")).toBeInTheDocument();
  });

  it("displays numeric parameter ranges correctly formatted", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByText("[0.0010, 0.1000]")).toBeInTheDocument();
    expect(screen.getByText("[0.0010, 0.2000]")).toBeInTheDocument();
    expect(screen.getByText("[16.0000, 256.0000]")).toBeInTheDocument();
  });

  it("displays categorical parameter ranges correctly formatted", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByText("adam, sgd, rmsprop")).toBeInTheDocument();
    expect(screen.getByText("adam, sgd")).toBeInTheDocument();
  });

  it("shows rationale text for each recommendation", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByText("Strong positive Spearman correlation (ρ=0.750) with accuracy")).toBeInTheDocument();
    expect(screen.getByText("Moderate correlation (ρ=-0.150) with accuracy")).toBeInTheDocument();
    expect(screen.getByText("ANOVA indicates categorical parameter")).toBeInTheDocument();
    expect(screen.getByText("Pareto knee point configuration uses weight_decay=0.0005")).toBeInTheDocument();
  });

  it("displays confidence percentages", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("55%")).toBeInTheDocument();
    expect(screen.getByText("78%")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("has refresh button that calls onRefresh", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    const refreshButton = screen.getByRole("button", { name: /refresh/i });
    fireEvent.click(refreshButton);
    expect(defaultProps.onRefresh).toHaveBeenCalledTimes(1);
  });

  it("shows target metric selector", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(screen.getByText("accuracy")).toBeInTheDocument();
  });

  it("expands/collapses recommendation details on click", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    const firstRecHeader = screen.getAllByRole("button", { name: /toggle details/i })[0];
    fireEvent.click(firstRecHeader);
    
    expect(screen.getByText("Parameter Type")).toBeInTheDocument();
    expect(screen.getByText("Numeric")).toBeInTheDocument();
    expect(screen.getByText("Current Range")).toBeInTheDocument();
    expect(screen.getByText("Recommended Range")).toBeInTheDocument();
  });

  it("displays top influential parameters in summary", () => {
    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} />
      </AuthProvider>
    );

    expect(screen.getByText("learning_rate")).toBeInTheDocument();
    expect(screen.getByText("optimizer")).toBeInTheDocument();
    expect(screen.getByText("weight_decay")).toBeInTheDocument();
    expect(screen.getByText("batch_size")).toBeInTheDocument();
  });
});

describe("TuningRecommendations Edge Cases", () => {
  it("handles empty recommendations gracefully", () => {
    const emptyData: TuningRecommendationsResponse = {
      experiment_id: "exp_empty",
      target_metric: "accuracy",
      recommendations: [],
      sensitivity_summary: {
        total_parameters_analyzed: 0,
        influential_parameters: 0,
        top_parameters: [],
      },
    };

    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} data={emptyData} />
      </AuthProvider>
    );

    expect(screen.getByText("No tuning recommendations available")).toBeInTheDocument();
  });

  it("handles missing Pareto knee config gracefully", () => {
    const noParetoData: TuningRecommendationsResponse = {
      ...mockTuningData,
      pareto_knee_config: undefined,
    };

    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} data={noParetoData} />
      </AuthProvider>
    );

    expect(screen.queryByText("Pareto Knee Point Configuration")).not.toBeInTheDocument();
  });

  it("handles single categorical value recommendation", () => {
    const singleCatData: TuningRecommendationsResponse = {
      ...mockTuningData,
      recommendations: [
        {
          parameter: "optimizer",
          parameter_type: "categorical",
          current_range: ["adam"],
          recommended_range: ["adam"],
          rationale: "Only one category tested",
          confidence: 0.5,
          priority: "low",
          source: "sensitivity",
        },
      ],
    };

    render(
      <AuthProvider>
        <TuningRecommendations {...defaultProps} data={singleCatData} />
      </AuthProvider>
    );

    expect(screen.getByText("adam")).toBeInTheDocument();
  });
});
