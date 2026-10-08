"""Real HTTP socket boundary tests for core create/read workflows."""

import socket
import threading
import time
import httpx
import pytest
import uvicorn
from backend.app.main import app


@pytest.fixture
def live_server_url():
    """Spin up live uvicorn server on a dynamically allocated loopback TCP port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    from backend.app.core.database import get_db, init_db
    from backend.tests.conftest import TestingSessionLocal, engine, Base
    Base.metadata.create_all(bind=engine)
    init_db()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Poll until server responds on real TCP socket
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            with httpx.Client(base_url=url, timeout=0.5) as probe:
                res = probe.get("/healthz")
                if res.status_code == 200:
                    break
        except Exception:
            time.sleep(0.05)
    else:
        server.should_exit = True
        app.dependency_overrides.pop(get_db, None)
        raise RuntimeError("Live uvicorn server failed to bind and start on loopback port")

    yield url

    server.should_exit = True
    app.dependency_overrides.pop(get_db, None)
    thread.join(timeout=3.0)


def test_real_http_boundary_create_read_lifecycle(live_server_url):
    """Test crossing the real HTTP/TCP boundary for authentication, create, read, and export."""
    with httpx.Client(base_url=live_server_url, timeout=10.0) as http_client:
        # 1. Real HTTP healthcheck probe
        health_res = http_client.get("/healthz")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"

        # 2. Login via demo-switch over real HTTP to get session cookie & CSRF token
        login_res = http_client.post("/api/v1/auth/demo-switch", json={"profile": "analyst"})
        assert login_res.status_code == 200
        login_data = login_res.json()
        csrf_token = login_data["csrf_token"]
        assert csrf_token

        headers = {"X-CSRF-Token": csrf_token}

        # 3. Create experiment over real HTTP POST boundary
        exp_payload = {
            "name": "Live HTTP Transformer Benchmark",
            "description": "Cross-socket TCP integration test",
            "domain": "ai-ml",
            "baseline_variant": "transformer_base",
        }
        create_exp_res = http_client.post("/api/v1/experiments", json=exp_payload, headers=headers)
        assert create_exp_res.status_code == 201
        exp_id = create_exp_res.json()["id"]
        assert exp_id.startswith("exp_")

        # 4. Read experiment back over real HTTP GET boundary
        get_exp_res = http_client.get(f"/api/v1/experiments/{exp_id}")
        assert get_exp_res.status_code == 200
        exp_record = get_exp_res.json()
        assert exp_record["name"] == "Live HTTP Transformer Benchmark"
        assert exp_record["baseline_variant"] == "transformer_base"

        # 5. Create run over real HTTP POST
        run_payload = {
            "experiment_id": exp_id,
            "name": "transformer_base_seed1",
            "variant_name": "transformer_base",
            "seed": 1,
            "hyperparameters": {"lr": 0.0003, "layers": 12},
            "metrics": {"eval_loss": 0.421, "throughput_tokens_per_sec": 1420.5},
            "tags": ["live-http-test"],
        }
        create_run_res = http_client.post("/api/v1/runs", json=run_payload, headers=headers)
        assert create_run_res.status_code == 201
        run_id = create_run_res.json()["id"]

        # 6. Read runs list back over real HTTP GET
        list_runs_res = http_client.get(f"/api/v1/runs?experiment_id={exp_id}")
        assert list_runs_res.status_code == 200
        runs_data = list_runs_res.json()
        assert runs_data["total"] == 1
        assert runs_data["items"][0]["id"] == run_id
        assert runs_data["items"][0]["metrics"]["eval_loss"] == 0.421

        # 7. Export markdown evaluation report over real HTTP GET
        report_res = http_client.get(f"/api/v1/export/experiments/{exp_id}/report.md")
        assert report_res.status_code == 200
        assert "text/markdown" in report_res.headers.get("content-type", "")
        assert "Live HTTP Transformer Benchmark" in report_res.text
        assert "Ryan Vo" in report_res.text
