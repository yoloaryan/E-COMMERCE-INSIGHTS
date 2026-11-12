"""
Verification Suite for Phase 20: Autonomous Cross-Engine Telemetry Watchdog.

Covers:
1. Baseline 4-engine Watchdog sweep across Inventory, Cohorts, Drift PSI, and Fraud.
2. Stress simulation & auto-remediation trigger lowering health score and emitting directives.
3. Scheduler configuration validation & interval clamping [15..3600].
4. FastAPI /api/v1/watchdog/status, /sweep, and /config endpoints with strict RBAC guard.
"""

from fastapi.testclient import TestClient

from src.api.security import SecurityRegistry
from src.api.server import app
from src.api.watchdog import AutonomousWatchdogEngine

client = TestClient(app)


def _login_as(email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_watchdog_baseline_and_stress_sweep():
    """Verify baseline vs stress 4-engine sweep health scoring and remediation triggers."""
    engine = AutonomousWatchdogEngine()
    baseline = engine.run_sweep(simulate_stress=False, auto_remediate=False, actor="pytest")

    assert 12.0 <= baseline["health_score"] <= 100.0
    assert len(baseline["subsystems"]) == 4
    keys = {s["key"] for s in baseline["subsystems"]}
    assert keys == {"inventory", "cohorts", "drift", "fraud"}

    stress = engine.run_sweep(simulate_stress=True, auto_remediate=True, actor="pytest")
    assert stress["stress_mode"] is True
    assert stress["health_score"] < baseline["health_score"]
    assert len(stress["directives"]) >= 2
    assert stress["remediation_triggered"] is not None
    assert len(engine.sweep_history) == 2


def test_watchdog_scheduler_config_clamping():
    """Verify interval clamping [15..3600] and scheduler enablement toggle."""
    engine = AutonomousWatchdogEngine()
    cfg_low = engine.configure(enabled=False, interval_seconds=2)
    assert cfg_low["enabled"] is False
    assert cfg_low["interval_seconds"] == 15

    cfg_high = engine.configure(enabled=True, interval_seconds=99999)
    assert cfg_high["enabled"] is True
    assert cfg_high["interval_seconds"] == 3600


def test_api_watchdog_endpoints_and_strict_rbac():
    """Verify GET status, POST sweep, POST config, and strict RBAC enforcement."""
    status_res = client.get("/api/v1/watchdog/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "online"
    assert len(status_data["latest"]["subsystems"]) == 4

    admin_token = _login_as("admin@nexusretail.ai", "NexusAdmin2026!")
    growth_token = _login_as("growth@nexusretail.ai", "NexusGrowth2026!")

    SecurityRegistry().strict_rbac_enabled = True
    try:
        anon = client.post("/api/v1/watchdog/sweep", json={"simulate_stress": False})
        assert anon.status_code == 401

        deny_growth = client.post(
            "/api/v1/watchdog/sweep",
            headers={"Authorization": f"Bearer {growth_token}"},
            json={"simulate_stress": False},
        )
        assert deny_growth.status_code == 403

        allow_admin = client.post(
            "/api/v1/watchdog/sweep",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"simulate_stress": True, "auto_remediate": True},
        )
        assert allow_admin.status_code == 200
        sweep_data = allow_admin.json()["sweep"]
        assert sweep_data["sweep_id"].startswith("SWP-")

        cfg_res = client.post(
            "/api/v1/watchdog/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"enabled": True, "interval_seconds": 120},
        )
        assert cfg_res.status_code == 200
        assert cfg_res.json()["scheduler"]["interval_seconds"] == 120
    finally:
        SecurityRegistry().strict_rbac_enabled = False
