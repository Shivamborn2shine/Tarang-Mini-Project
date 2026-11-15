"""Sprint 1 integration tests for TARANG FastAPI backend."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

# Use an isolated test SQLite DB before importing app.db
TEST_DB_PATH = API_ROOT / "test_sprint1.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
os.environ["TARANG_DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def _make_wifi_obs(session_id: str, device_id: str, idx: int) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": 1,
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "device_id": device_id,
        "kind": "wifi",
        "technology": "wifi_5ghz",
        "source": "android_wifi",
        "observed_at": ts,
        "recorded_at": ts,
        "freshness_ms": 250,
        "location": {
            "kind": "indoor",
            "floorplan_id": str(uuid.uuid4()),
            "x_norm": round((idx % 100) / 100.0, 2),
            "y_norm": round((idx // 100) / 10.0, 2),
        },
        "metrics": {"rssi_dbm": -55 - (idx % 30), "frequency_mhz": 5180, "quality_percent": None},
        "network": {"ssid": "HomeSurvey5G", "bssid_hash": "9c3f1a8d2e7b4c01", "is_connected": True},
        "flags": [],
    }


def test_sprint1_500_observations_idempotent_retry_and_export() -> None:
    with TestClient(app) as client:
        # 1. Health
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        # 2. Project + Device + Session
        proj = client.post("/api/v1/projects", json={"name": "Home Survey", "map_mode": "indoor"})
        assert proj.status_code == 201
        project_id = proj.json()["id"]

        device_id = str(uuid.uuid4())
        dev = client.post(
            "/api/v1/devices/register",
            json={
                "id": device_id,
                "platform": "android",
                "model": "Pixel Test",
                "os_version": "14",
                "app_version": "0.1.0",
                "capability_json": {"wifi": True, "lte": True},
            },
        )
        assert dev.status_code == 201

        sess = client.post(
            "/api/v1/sessions",
            json={"project_id": project_id, "device_id": device_id, "settings_json": {"interval_s": 5}},
        )
        assert sess.status_code == 201
        session_id = sess.json()["id"]

        # 3. Sprint 1 Gate: ingest 500 synthetic observations
        batch_id = str(uuid.uuid4())
        observations = [_make_wifi_obs(session_id, device_id, i) for i in range(500)]
        resp1 = client.post(
            "/api/v1/observations/batch",
            json={"batch_id": batch_id, "device_id": device_id, "observations": observations},
        )
        assert resp1.status_code == 200
        body1 = resp1.json()
        assert body1["accepted_count"] == 500
        assert body1["duplicate_count"] == 0
        assert body1["rejected_count"] == 0

        # 4. Retry exact same batch -> 0 accepted, 500 duplicates
        resp2 = client.post(
            "/api/v1/observations/batch",
            json={"batch_id": batch_id, "device_id": device_id, "observations": observations},
        )
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["accepted_count"] == 0
        assert body2["duplicate_count"] == 500
        assert body2["rejected_count"] == 0

        # 5. Query session observations & summary
        q = client.get(f"/api/v1/sessions/{session_id}/observations?limit=100&offset=0")
        assert q.status_code == 200
        assert q.json()["total"] == 500
        assert len(q.json()["items"]) == 100

        summary = client.get(f"/api/v1/projects/{project_id}/summary")
        assert summary.status_code == 200
        assert summary.json()["total_observations"] == 500
        assert summary.json()["by_kind"]["wifi"] == 500

        # 6. CSV export redacts SSID by default
        csv_resp = client.get(f"/api/v1/projects/{project_id}/export?format=csv")
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers["content-type"]
        assert "<REDACTED>" in csv_resp.text
        assert "HomeSurvey5G" not in csv_resp.text


def test_partial_batch_rejection_does_not_drop_valid_items() -> None:
    with TestClient(app) as client:
        proj = client.post("/api/v1/projects", json={"name": "Outdoor Walk", "map_mode": "outdoor"}).json()
        device_id = str(uuid.uuid4())
        client.post(
            "/api/v1/devices/register",
            json={
                "id": device_id,
                "platform": "windows",
                "model": "Win11 Laptop",
                "os_version": "26300",
                "app_version": "0.1.0",
            },
        )
        sess = client.post(
            "/api/v1/sessions",
            json={"project_id": proj["id"], "device_id": device_id},
        ).json()

        valid_obs = _make_wifi_obs(sess["id"], device_id, 0)
        bad_obs = {"schema_version": 99, "id": str(uuid.uuid4())}

        resp = client.post(
            "/api/v1/observations/batch",
            json={"batch_id": str(uuid.uuid4()), "device_id": device_id, "observations": [valid_obs, bad_obs]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted_count"] == 1
        assert data["rejected_count"] == 1
        assert data["outcomes"][0]["status"] == "accepted"
        assert data["outcomes"][1]["status"] == "rejected"
