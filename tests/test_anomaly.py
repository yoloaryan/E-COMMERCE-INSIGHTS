"""
Unit and Integration Tests for Transaction Anomaly, Fraud & Cancellation Intelligence Engine.
"""

from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.api.server import app
from src.models.anomaly_detection import AnomalyDetectionEngine, AnomalyRegistry

client = TestClient(app)


def _login_as(email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_anomaly_engine_synthetic_fallback():
    """Verify Isolation Forest engine initializes and audits synthetic fallback cleanly."""
    engine = AnomalyDetectionEngine(data_path=Path("/tmp/non_existent_retail_fraud_p15.parquet"))
    assert engine.data_source == "synthetic_fallback"

    report = engine.generate_anomaly_report()
    assert report["status"] == "success"
    assert report["summary"]["total_invoices_scanned"] > 500
    assert report["summary"]["flagged_anomalies_count"] > 0
    assert len(report["country_cancellation_rates"]) >= 3
    assert len(report["top_anomalous_invoices"]) >= 3


def test_score_normal_vs_extreme_transaction():
    """Verify low-risk retail order vs extreme off-hours guest whale outlier separation."""
    engine = AnomalyDetectionEngine(data_path=Path("/tmp/non_existent_score_p15.parquet"))

    normal = engine.score_transaction(
        amount_gbp=65.40,
        total_units=12,
        line_items=4,
        customer_id="17850",
        country="United Kingdom",
        hour_of_day=14.0,
        is_guest=False,
        is_cancelled=False,
        auto_quarantine=False,
    )
    assert normal["risk_score"] < 40.0
    assert normal["risk_tier"] in ("LOW_SAFE", "ELEVATED_MONITOR")
    assert normal["recommended_action"] in ("AUTO_APPROVE", "LOG_AND_MONITOR")

    extreme = engine.score_transaction(
        amount_gbp=28500.00,
        total_units=18000,
        line_items=1,
        customer_id="Guest",
        country="United Kingdom",
        hour_of_day=2.0,
        is_guest=True,
        is_cancelled=False,
        auto_quarantine=False,
    )
    assert extreme["risk_score"] >= 75.0
    assert extreme["risk_tier"] == "CRITICAL_QUARANTINE"
    assert extreme["recommended_action"] == "QUARANTINE_AND_HOLD"
    assert extreme["isolation_forest_anomaly"] is True
    assert len(extreme["triggered_signals"]) >= 3


def test_cancellation_history_and_negative_invoice_risk():
    """Verify cancellation reversals and repeat-canceller history elevate risk score."""
    engine = AnomalyDetectionEngine(data_path=Path("/tmp/non_existent_cancel_p15.parquet"))

    res = engine.score_transaction(
        amount_gbp=-3200.0,
        total_units=450,
        line_items=2,
        customer_id="14096",
        hour_of_day=11.0,
        is_cancelled=True,
        historical_cancel_rate=0.65,
        auto_quarantine=False,
    )
    assert res["risk_score"] >= 50.0
    assert any("cancellation rate" in s.lower() for s in res["triggered_signals"])
    assert any("cancelled" in s.lower() for s in res["triggered_signals"])


def test_quarantine_enqueue_and_resolve():
    """Verify high-risk auto-quarantine and valid/invalid operator triage decisions."""
    engine = AnomalyDetectionEngine(data_path=Path("/tmp/non_existent_quarantine_p15.parquet"))
    scored = engine.score_transaction(
        amount_gbp=19500.0,
        total_units=6500,
        line_items=1,
        customer_id="Guest",
        hour_of_day=1.0,
        is_guest=True,
        invoice_no="INV-TESTQ01",
        auto_quarantine=True,
    )
    alert_id = scored["alert_id"]
    assert alert_id.startswith("FRD-")

    resolved = AnomalyRegistry().resolve_alert(alert_id, "BLOCKED", "admin@nexusretail.ai")
    assert resolved is not None
    assert resolved["status"] == "BLOCKED"
    assert resolved["resolved_by"] == "admin@nexusretail.ai"

    with pytest.raises(ValueError):
        AnomalyRegistry().resolve_alert(alert_id, "INVALID_DECISION", "admin@nexusretail.ai")


def test_api_fraud_anomaly_report_endpoint():
    """Assert GET /api/v1/fraud/anomaly-report returns summary, country rates, and queue."""
    res = client.get("/api/v1/fraud/anomaly-report")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "IsolationForest" in data["model"]
    assert data["summary"]["total_invoices_scanned"] > 0
    assert len(data["country_cancellation_rates"]) > 0
    assert len(data["quarantine_queue"]) >= 2


def test_api_fraud_score_transaction_endpoint():
    """Assert POST /api/v1/fraud/score-transaction evaluates risk and auto-quarantines outliers."""
    payload = {
        "amount_gbp": 24000.0,
        "total_units": 9000,
        "line_items": 1,
        "customer_id": "Guest",
        "country": "United Kingdom",
        "hour_of_day": 3.0,
        "is_guest": True,
        "auto_quarantine": True,
    }
    res = client.post("/api/v1/fraud/score-transaction", json=payload)
    assert res.status_code == 200
    assessment = res.json()["assessment"]
    assert assessment["risk_score"] >= 75.0
    assert assessment["risk_tier"] == "CRITICAL_QUARANTINE"
    assert "alert_id" in assessment


def test_api_fraud_quarantine_resolve_rbac_and_errors():
    """Verify RBAC guard on /fraud/quarantine/{id}/resolve plus 400/404 validation."""
    growth_token = _login_as("growth@nexusretail.ai", "NexusGrowth2026!")
    supply_token = _login_as("supply@nexusretail.ai", "NexusOps2026!")

    # Growth lacks fraud:resolve permission -> 403 Forbidden
    deny = client.post(
        "/api/v1/fraud/quarantine/FRD-581483/resolve",
        headers={"Authorization": f"Bearer {growth_token}"},
        json={"decision": "APPROVED"},
    )
    assert deny.status_code == 403

    # Supply VP has fraud:resolve permission -> 200 OK
    allow = client.post(
        "/api/v1/fraud/quarantine/FRD-574941/resolve",
        headers={"Authorization": f"Bearer {supply_token}"},
        json={"decision": "APPROVED"},
    )
    assert allow.status_code == 200
    assert allow.json()["alert"]["status"] == "APPROVED"

    # Invalid decision -> 400; missing alert -> 404
    bad_dec = client.post("/api/v1/fraud/quarantine/FRD-581483/resolve", json={"decision": "MAYBE"})
    assert bad_dec.status_code == 400

    missing = client.post("/api/v1/fraud/quarantine/FRD-DOESNOTEXIST/resolve", json={"decision": "BLOCKED"})
    assert missing.status_code == 404


def test_pos_inject_and_webhook_include_fraud_assessment():
    """Assert POS order injection and webhook simulation automatically compute fraud risk score."""
    pos_res = client.post("/api/v1/orders/inject", json={
        "customer_id": "17850",
        "country": "United Kingdom",
        "items": [{"stock_code": "22423", "description": "Regency Cakestand 3 Tier", "quantity": 5, "unit_price": 10.95}],
    })
    assert pos_res.status_code == 200
    pos_order = pos_res.json()["order"]
    assert "fraud_assessment" in pos_order
    assert 0.0 <= pos_order["fraud_assessment"]["risk_score"] <= 100.0

    wh_res = client.post("/api/v1/integrations/webhook/simulate-sample", json={"provider": "shopify"})
    assert wh_res.status_code == 200
    wh_data = wh_res.json()
    assert "fraud_assessment" in wh_data
    assert "risk_tier" in wh_data["fraud_assessment"]


def test_unseen_customer_default_cancel_rate_and_clamping():
    """Verify unseen customer IDs default to 0% cancel rate and scores remain bounded [2..99.5]."""
    engine = AnomalyDetectionEngine(data_path=Path("/tmp/non_existent_bounds_p15.parquet"))
    res = engine.score_transaction(
        amount_gbp=12.0,
        total_units=2,
        line_items=1,
        customer_id="NEW_UNSEEN_999999",
        auto_quarantine=False,
    )
    assert res["historical_cancel_rate_pct"] == 0.0
    assert 2.0 <= res["risk_score"] <= 99.5


def test_api_fraud_strict_rbac_enforcement():
    """Verify strict RBAC policy blocks anonymous /fraud/score-transaction calls with 401."""
    from src.api.security import SecurityRegistry

    token = _login_as("admin@nexusretail.ai", "NexusAdmin2026!")
    SecurityRegistry().strict_rbac_enabled = True
    try:
        anon = client.post("/api/v1/fraud/score-transaction", json={"amount_gbp": 120.0})
        assert anon.status_code == 401

        authed = client.post(
            "/api/v1/fraud/score-transaction",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount_gbp": 120.0, "total_units": 4, "auto_quarantine": False},
        )
        assert authed.status_code == 200
    finally:
        SecurityRegistry().strict_rbac_enabled = False

