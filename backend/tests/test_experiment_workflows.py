"""End-to-end tests for experiment tracking, run diffs, artifacts, audit logs, and export/import."""

import os
import tempfile
from backend.app.core.security import calculate_sha256
from backend.app.models.entities import AuditLog


def test_experiment_and_run_full_lifecycle(analyst_client, db_session):
    """Full lifecycle: create experiment, create runs, list with filter, update, verify."""
    client, headers = analyst_client

    # 1. Create experiment
    exp_res = client.post(
        "/api/v1/experiments",
        json={"name": "Vision Transformer Fine-Tuning", "description": "ViT-B/16 vs ViT-L/16", "baseline_variant": "vit_base"},
        headers=headers,
    )
    assert exp_res.status_code == 201
    exp_id = exp_res.json()["id"]

    # 2. Create runs
    run1_res = client.post(
        "/api/v1/runs",
        json={
            "experiment_id": exp_id,
            "name": "vit_base_seed42",
            "variant_name": "vit_base",
            "seed": 42,
            "hyperparameters": {"lr": 1e-4, "batch_size": 32, "optimizer": "adamw"},
            "metrics": {"accuracy": 0.842, "latency_ms": 14.5},
            "tags": ["baseline", "seed42"],
        },
        headers=headers,
    )
    assert run1_res.status_code == 201
    run1_id = run1_res.json()["id"]

    run2_res = client.post(
        "/api/v1/runs",
        json={
            "experiment_id": exp_id,
            "name": "vit_large_seed42",
            "variant_name": "vit_large",
            "seed": 42,
            "hyperparameters": {"lr": 5e-5, "batch_size": 16, "optimizer": "adamw"},
            "metrics": {"accuracy": 0.881, "latency_ms": 28.2},
            "tags": ["treatment", "seed42"],
        },
        headers=headers,
    )
    assert run2_res.status_code == 201
    run2_id = run2_res.json()["id"]

    # 3. List runs with variant filter
    list_res = client.get(f"/api/v1/runs?experiment_id={exp_id}&variant_name=vit_base")
    assert list_res.status_code == 200
    runs = list_res.json()["items"]
    assert len(runs) == 1
    assert runs[0]["variant_name"] == "vit_base"

    # 4. Run diff
    diff_res = client.get(f"/api/v1/runs/diff?base_run_id={run1_id}&target_run_id={run2_id}")
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    lr_delta = next(p for p in diff_data["parameter_deltas"] if p["parameter"] == "lr")
    assert lr_delta["changed"] is True

    acc_delta = next(m for m in diff_data["metric_deltas"] if m["metric"] == "accuracy")
    assert acc_delta["improved"] is True
    assert acc_delta["absolute_delta"] > 0


def test_artifact_registration_and_checksum_verification(analyst_client):
    """Register artifact manifest and perform cryptographic SHA-256 integrity check."""
    client, headers = analyst_client

    # Create experiment and run
    exp = client.post("/api/v1/experiments", json={"name": "Artifact Test Exp"}, headers=headers).json()
    run = client.post(
        "/api/v1/runs",
        json={"experiment_id": exp["id"], "name": "run1", "variant_name": "v1", "seed": 42},
        headers=headers,
    ).json()

    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        content = b"Model checkpoint binary weights simulated payload."
        tf.write(content)
        temp_path = tf.name

    expected_sha = calculate_sha256(content)

    try:
        # Register artifact
        art_res = client.post(
            f"/api/v1/runs/{run['id']}/artifacts",
            json={
                "run_id": run["id"],
                "name": "model_best.pt",
                "artifact_type": "checkpoint",
                "file_path": temp_path,
                "file_size_bytes": len(content),
                "sha256_hash": expected_sha,
            },
            headers=headers,
        )
        assert art_res.status_code == 201
        art_id = art_res.json()["id"]

        # Verify artifact checksum
        verify_res = client.post(f"/api/v1/artifacts/{art_id}/verify", headers=headers)
        assert verify_res.status_code == 200
        assert verify_res.json()["verified"] is True
        assert verify_res.json()["actual_sha256"] == expected_sha

        # Simulate file corruption / tampering
        with open(temp_path, "wb") as tf2:
            tf2.write(b"Tampered corrupted weights file.")

        tampered_verify = client.post(f"/api/v1/artifacts/{art_id}/verify", headers=headers)
        assert tampered_verify.status_code == 200
        assert tampered_verify.json()["verified"] is False
        assert "CHECKSUM MISMATCH" in tampered_verify.json()["message"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_audit_log_tracking(admin_client, db_session):
    """Ensure transactional operations record structured audit trail."""
    client, headers = admin_client

    exp_res = client.post("/api/v1/experiments", json={"name": "Audited Exp"}, headers=headers)
    assert exp_res.status_code == 201
    exp_id = exp_res.json()["id"]

    logs = db_session.query(AuditLog).filter(AuditLog.resource_id == exp_id).all()
    assert len(logs) >= 1
    assert logs[0].action == "CREATE_EXPERIMENT"
    assert logs[0].user_email == "ryandtvo@gmail.com"


def test_export_and_import_bundle(analyst_client):
    """Test exporting reproducible JSON experiment bundle and importing it."""
    client, headers = analyst_client

    # Create source experiment with 2 runs
    exp = client.post("/api/v1/experiments", json={"name": "Source Exp for Bundle"}, headers=headers).json()
    client.post(
        "/api/v1/runs",
        json={
            "experiment_id": exp["id"],
            "name": "r1",
            "variant_name": "v1",
            "seed": 42,
            "metrics": {"accuracy": 0.91},
        },
        headers=headers,
    )

    # Export bundle
    export_res = client.get(f"/api/v1/export/experiments/{exp['id']}")
    assert export_res.status_code == 200
    bundle = export_res.json()
    assert bundle["format"] == "experiment-comparison-hub-bundle"
    assert len(bundle["runs"]) == 1

    # Modify name for import
    bundle["experiment"]["name"] = "Imported Replicated Experiment"

    # Import bundle
    import_res = client.post("/api/v1/import", json={"bundle": bundle}, headers=headers)
    assert import_res.status_code == 201
    import_data = import_res.json()
    assert import_data["runs_imported"] == 1
    assert import_data["experiment"]["name"] == "Imported Replicated Experiment"
