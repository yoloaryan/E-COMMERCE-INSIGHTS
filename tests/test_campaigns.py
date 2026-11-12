"""
Unit and Integration Tests for Retention Campaign Dispatcher & Multi-Channel Alert System.
"""

from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.api.server import app
from src.api.campaigns import (
    VoucherGenerator,
    MessageFormatter,
    CampaignRegistry,
    CampaignDispatcher,
    WatchdogEvaluator
)

client = TestClient(app)


def test_voucher_generator():
    """Assert voucher codes adhere to expected format and expiration."""
    code = VoucherGenerator.generate_voucher_code(prefix="WINBACK", discount_pct=20, length=5)
    assert code.startswith("WINBACK-20-")
    assert len(code.split("-")[-1]) == 5

    exp = VoucherGenerator.calculate_expiration(days_valid=7)
    assert "UTC" in exp


def test_message_formatter_slack():
    """Assert Slack Block Kit structure contains required elements."""
    payload = MessageFormatter.build_slack_blocks(
        title="Test Campaign",
        message="Special 15% discount for you",
        audience_segment="At-Risk Cohort",
        audience_size=42,
        revenue_target_gbp=15200.50,
        voucher_code="WIN-15-XYZ99",
        discount_pct=15,
        severity="critical"
    )
    assert "blocks" in payload
    assert len(payload["blocks"]) >= 4
    assert "WIN-15-XYZ99" in str(payload["blocks"])


def test_message_formatter_discord():
    """Assert Discord Embed payload contains title and fields."""
    payload = MessageFormatter.build_discord_embed(
        title="Test Churn Alert",
        message="Account #14096 is lapsing",
        audience_segment="VIPs",
        audience_size=1,
        revenue_target_gbp=3400.0,
        voucher_code="VIP-20-AAA11",
        discount_pct=20,
        severity="warning"
    )
    assert "embeds" in payload
    assert len(payload["embeds"]) == 1
    fields = payload["embeds"][0]["fields"]
    assert any(f["name"] == "Voucher Code" for f in fields)


def test_message_formatter_email():
    """Assert HTML email contains customer greeting and voucher code."""
    html = MessageFormatter.build_html_email(
        customer_name="John Doe",
        discount_pct=15,
        voucher_code="WINBACK-15-TEST1",
        expires_at="2026-11-20"
    )
    assert "John Doe" in html
    assert "WINBACK-15-TEST1" in html
    assert "15% discount" in html


def test_campaign_dispatcher_execution():
    """Assert CampaignDispatcher generates voucher and records dispatch."""
    res = CampaignDispatcher.dispatch_campaign(
        campaign_name="Automated Win-Back Q4",
        audience_segment="At-Risk Customers",
        audience_size=25,
        revenue_target_gbp=8500.0,
        discount_pct=15,
        channels=["slack", "discord", "email"]
    )
    assert res["status"] == "success"
    camp = res["campaign"]
    assert camp["name"] == "Automated Win-Back Q4"
    assert "slack" in camp["channels_delivered"]
    assert "discord" in camp["channels_delivered"]
    assert "email" in camp["channels_delivered"]
    assert camp["voucher_code"] in CampaignRegistry().generated_vouchers


def test_watchdog_evaluator_churn():
    """Assert Churn Watchdog triggers on high-value at-risk accounts."""
    # Breaches criteria: churn 0.85 >= 0.65 and spend 2500 >= 1000
    triggered = WatchdogEvaluator.evaluate_churn_watchdog(
        customer_id=14096,
        churn_prob=0.85,
        total_spend_gbp=2500.0
    )
    assert triggered is not None
    assert triggered["triggered"] is True
    assert triggered["customer_id"] == 14096

    # Safe customer: churn 0.20 < 0.65 -> not triggered
    safe = WatchdogEvaluator.evaluate_churn_watchdog(
        customer_id=17850,
        churn_prob=0.20,
        total_spend_gbp=5000.0
    )
    assert safe is None


def test_watchdog_evaluator_drift():
    """Assert Drift Watchdog triggers on critical PSI divergence."""
    # Breaches criteria: PSI 0.32 >= 0.25
    alert = WatchdogEvaluator.evaluate_drift_watchdog(
        psi_score=0.32,
        shifted_features=["UnitPrice", "Quantity"]
    )
    assert alert is not None
    assert alert["triggered"] is True
    assert alert["psi_score"] == 0.32

    # Normal PSI 0.05 < 0.25 -> not triggered
    normal = WatchdogEvaluator.evaluate_drift_watchdog(
        psi_score=0.05,
        shifted_features=[]
    )
    assert normal is None


def test_api_campaigns_status_endpoint():
    """Assert GET /api/v1/campaigns/status returns channel configs and metrics."""
    res = client.get("/api/v1/campaigns/status")
    assert res.status_code == 200
    data = res.json()
    assert "channels" in data
    assert "slack" in data["channels"]
    assert "discord" in data["channels"]
    assert "email" in data["channels"]
    assert "watchdogs" in data
    assert "churn_watchdog" in data["watchdogs"]


def test_api_configure_channels_endpoint():
    """Assert POST /api/v1/campaigns/configure-channels updates webhook URL."""
    res = client.post("/api/v1/campaigns/configure-channels", json={
        "channel": "slack",
        "webhook_url": "https://hooks.slack.com/services/T00/B00/X00",
        "enabled": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["channel_status"]["status"] == "LIVE_CONNECTED"

    # Bad channel
    bad = client.post("/api/v1/campaigns/configure-channels", json={
        "channel": "unsupported_channel",
        "enabled": True
    })
    assert bad.status_code == 400


def test_api_dispatch_campaign_endpoint():
    """Assert POST /api/v1/campaigns/dispatch executes and returns campaign payload."""
    payload = {
        "campaign_name": "VIP Holiday Retention",
        "audience_segment": "Champions & Loyalists",
        "audience_size": 150,
        "revenue_target_gbp": 45000.0,
        "discount_pct": 20,
        "channels": ["slack", "email"]
    }
    res = client.post("/api/v1/campaigns/dispatch", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "campaign" in data
    assert data["campaign"]["discount_pct"] == 20
    assert len(data["campaign"]["voucher_code"]) > 5


def test_api_test_channel_endpoint():
    """Assert POST /api/v1/campaigns/test-channel handles slack, discord, and email pings."""
    for ch in ["slack", "discord", "email"]:
        res = client.post("/api/v1/campaigns/test-channel", json={"channel": ch})
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        assert res.json()["channel"] == ch


def test_api_trigger_watchdog_endpoint():
    """Assert POST /api/v1/campaigns/trigger-watchdog processes churn and drift."""
    # Test churn trigger
    res_churn = client.post("/api/v1/campaigns/trigger-watchdog", json={
        "watchdog_type": "churn",
        "customer_id": 14096,
        "churn_prob": 0.88,
        "total_spend_gbp": 3200.0
    })
    assert res_churn.status_code == 200
    assert res_churn.json()["triggered"] is True

    # Test drift trigger
    res_drift = client.post("/api/v1/campaigns/trigger-watchdog", json={
        "watchdog_type": "drift",
        "psi_score": 0.35,
        "shifted_features": ["UnitPrice"]
    })
    assert res_drift.status_code == 200
    assert res_drift.json()["triggered"] is True
