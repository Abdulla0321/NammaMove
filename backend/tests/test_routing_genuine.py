"""Full HTTP API benchmark using genuine local Supabase and actual OTP."""

import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.engine import make_url
from test_routing import query


@pytest.mark.otp
@pytest.mark.supabase
def test_real_auth_routing_api_and_four_concurrent_latency():
    source = os.environ.get("NAMMAMOVE_SUPABASE_ACCEPTANCE_CONFIG")
    folder = os.environ.get("NAMMAMOVE_TEST_OTP_DIR")
    url = os.environ.get("NAMMAMOVE_TEST_OTP_URL")
    if not source or not folder or not url:
        pytest.skip("Actual Supabase acceptance config and OTP fixture service required")
    config = json.loads(Path(source).read_text())
    assert urlsplit(config["supabase_url"]).hostname in {"localhost", "127.0.0.1"}
    db = make_url(config["database_url"])
    assert db.database and db.database.endswith("_test")
    user = config["users"][0]
    with httpx.Client(timeout=10) as client:
        result = client.post(
            config["supabase_url"] + "/auth/v1/token?grant_type=password",
            json={"email": user["email"], "password": user["password"]},
        )
        assert result.status_code == 200
        headers = {"Authorization": "Bearer " + result.json()["access_token"]}
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=SecretStr(config["database_url"]),
        supabase_url=config["supabase_url"],
        otp_url=url,
        otp_manifest=Path(folder) / "manifest.json",
        simulation_enabled=True,
    )
    with TestClient(create_app(settings)) as api:
        assert api.get("/health/ready").status_code == 200
        payload = query().model_dump(mode="json")
        assert api.post("/v1/routing/plan", json=payload).status_code == 401
        # Cold graph loading/JIT is readiness work, not steady-state latency.
        readiness_probes = 0
        for _ in range(10):
            readiness_probes += 1
            ready = api.post("/v1/routing/plan", json=payload, headers=headers)
            if ready.status_code == 200:
                break
            assert ready.status_code == 503
            time.sleep(1)
        assert ready.status_code == 200
        for _ in range(2):
            warm = api.post("/v1/routing/plan", json=payload, headers=headers)
        assert warm.status_code == 200
        expected = warm.json()["graph_id"]

        def run(_):
            start = time.perf_counter()
            response = api.post("/v1/routing/plan", json=payload, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["graph_id"] == expected and data["data_mode"] == "simulation"
            assert [leg["mode"] for leg in data["itineraries"][0]["legs"]] == [
                "BUS",
                "WALK",
                "SUBWAY",
            ]
            return time.perf_counter() - start

        with ThreadPoolExecutor(max_workers=4) as pool:
            durations = list(pool.map(run, range(40)))
        p95 = sorted(durations)[math.ceil(0.95 * len(durations)) - 1]
        assert p95 < 2
        evidence = os.environ.get("NAMMAMOVE_ROUTING_EVIDENCE")
        if evidence:
            manifest = json.loads((Path(folder) / "manifest.json").read_text())
            Path(evidence).write_text(
                json.dumps(
                    {
                        "graph_id": expected,
                        "graph_sha256": manifest["graph_sha256"],
                        "otp_image": manifest["otp_image"],
                        "inputs": manifest["inputs"],
                        "data_mode": "simulation",
                        "geography": "independently authored grid, not real OSM streets",
                        "gtfs": "independently authored fixture, not actual schedules",
                        "auth": "genuine local Supabase ES256/JWKS; configured non-owner API login",
                        "http_api_requests": 40,
                        "concurrency": 4,
                        "warmup_requests": 2,
                        "readiness_probes": readiness_probes,
                        "p95_ms": round(p95 * 1000, 2),
                        "max_ms": round(max(durations) * 1000, 2),
                        "failures": 0,
                        "target_p95_ms": 2000,
                        "scope": "steady-state synthetic fixture; not city-scale or cold-start certification",
                    },
                    indent=2,
                )
                + "\n"
            )
