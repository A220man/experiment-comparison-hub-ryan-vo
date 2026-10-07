"""Tests for LLM advisory explanation (offline fallback and mocked provider) and sensitivity analysis."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from backend.app.core.config import settings


def test_offline_deterministic_advisory_explanation(analyst_client):
    """When LLM_API_KEY is unset, advisory endpoint must deterministically fall back without failing."""
    client, headers = analyst_client

    exp = client.post("/api/v1/experiments", json={"name": "LLM Test Exp", "baseline_variant": "base"}, headers=headers).json()

    # Add 2 baseline runs and 2 treatment runs
    for s in [1, 2]:
        client.post(
            "/api/v1/runs",
            json={
                "experiment_id": exp["id"],
                "name": f"base_{s}",
                "variant_name": "base",
                "seed": s,
                "metrics": {"accuracy": 0.80, "latency_ms": 10.0},
            },
            headers=headers,
        )
        client.post(
            "/api/v1/runs",
            json={
                "experiment_id": exp["id"],
                "name": f"treat_{s}",
                "variant_name": "treat",
                "seed": s,
                "metrics": {"accuracy": 0.90, "latency_ms": 8.0},
            },
            headers=headers,
        )

    # Request advisory explanation
    res = client.post(
        "/api/v1/analysis/advisory-explanation",
        json={"experiment_id": exp["id"], "analysis_type": "comprehensive"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_advisory"] is True
    assert data["offline_fallback"] is True
    assert "Advisory only" in data["disclaimer"]
    assert "Deterministic Empirical Advisory Summary" in data["advisory_text"]


@patch("backend.app.services.llm_service.httpx.AsyncClient.post")
def test_mocked_llm_provider_call(mock_post, analyst_client):
    """Test mocked external LLM provider call with secret key configured."""
    client, headers = analyst_client

    # Set mock key and provider
    settings.llm_api_key = "test-operator-secret-key"
    settings.llm_provider = "openai"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "The treatment variant achieves superior accuracy with reduced latency. The knee point optimal trade-off is achieved."
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    try:
        exp = client.post("/api/v1/experiments", json={"name": "Mocked LLM Exp"}, headers=headers).json()
        client.post(
            "/api/v1/runs",
            json={
                "experiment_id": exp["id"],
                "name": "r1",
                "variant_name": "v1",
                "seed": 42,
                "metrics": {"accuracy": 0.95, "latency_ms": 12.0},
            },
            headers=headers,
        )

        res = client.post(
            "/api/v1/analysis/advisory-explanation",
            json={"experiment_id": exp["id"]},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["offline_fallback"] is False
        assert "treatment variant achieves superior accuracy" in data["advisory_text"]
    finally:
        settings.llm_api_key = None


def test_sensitivity_analysis_api(analyst_client):
    """Test parameter sensitivity correlation analysis via API."""
    client, headers = analyst_client

    exp = client.post("/api/v1/experiments", json={"name": "Sweep Exp"}, headers=headers).json()

    # Create parameter sweep runs
    for lr, acc in [(1e-5, 0.70), (1e-4, 0.82), (1e-3, 0.91), (1e-2, 0.65)]:
        client.post(
            "/api/v1/runs",
            json={
                "experiment_id": exp["id"],
                "name": f"run_lr_{lr}",
                "variant_name": "sweep",
                "seed": 42,
                "hyperparameters": {"lr": lr, "optimizer": "adamw"},
                "metrics": {"accuracy": acc},
            },
            headers=headers,
        )

    res = client.post(
        "/api/v1/analysis/sensitivity",
        json={"experiment_id": exp["id"], "target_metric": "accuracy"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_runs_analyzed"] == 4
    lr_param = next(p for p in data["parameters"] if p["parameter"] == "lr")
    assert lr_param["parameter_type"] == "numeric"
    assert lr_param["importance_score"] > 0
