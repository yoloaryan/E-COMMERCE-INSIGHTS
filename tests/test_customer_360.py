"""
Verification Suite for Phase 24: Unified Customer-360 Intelligence & Ledger API.

Covers:
1. Customer360Engine deterministic synthetic fallback & profile accounting metrics.
2. Paginated ledger filtering by segment and ID/country search string.
3. Single-customer 360 dossier retrieval with return rate, churn prob & NBA action.
4. FastAPI /api/v1/customers/ledger and /api/v1/customers/{id}/360 (including 404).
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.models.customer_360 import Customer360Engine

client = TestClient(app)


def test_customer_360_engine_profiles_and_ledger_queries():
    """Verify Customer360Engine builds complete dossiers and supports filtering."""
    engine = Customer360Engine(use_parquet=False)
    assert engine.data_source == "synthetic_fallback"

    all_res = engine.query_ledger(segment="all", search="", limit=10)
    assert all_res["status"] == "success"
    assert len(all_res["customers"]) == 10
    assert all_res["total_catalog_customers"] >= 15

    vip_res = engine.query_ledger(segment="Champions (VIP)", limit=20)
    assert all(c["segment"] == "Champions (VIP)" for c in vip_res["customers"])

    profile = engine.get_customer_profile("14646")
    assert profile is not None
    assert profile["country"] == "Netherlands"
    assert 0.0 <= profile["return_rate_pct"] <= 100.0
    assert profile["next_best_action"]


def test_api_customer_360_endpoints():
    """Verify FastAPI /customers/ledger and /customers/{id}/360 endpoints including 404."""
    led = client.get("/api/v1/customers/ledger?segment=all&search=14646&limit=5")
    assert led.status_code == 200
    l_data = led.json()
    assert l_data["total_catalog_customers"] >= 15
    assert any(c["id"] == "14646" for c in l_data["customers"])

    c360 = client.get("/api/v1/customers/14646/360")
    assert c360.status_code == 200
    prof = c360.json()["profile"]
    assert prof["customer_id"] == "14646"
    assert len(prof["history"]) >= 1

    missing = client.get("/api/v1/customers/UNKNOWN_CUST_999999/360")
    assert missing.status_code == 404

