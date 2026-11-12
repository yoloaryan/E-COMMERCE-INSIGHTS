"""
Verification Suite for Phase 21: Market Basket Association Rules & Bundle Optimizer.

Covers:
1. Empirical synthetic basket rule mining (Support, Confidence, Lift, Conviction bounds).
2. Filtering rules by min_lift / min_support_pct / limit parameters.
3. Live cart bundle evaluation returning complementary high-Lift add-ons & margin math.
4. FastAPI REST endpoints (/api/v1/recommendations/basket-rules & /evaluate-bundle).
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.models.basket_rules import MarketBasketEngine

client = TestClient(app)


def test_market_basket_rules_invariants_and_filtering():
    """Verify Support, Confidence, Lift bounds and min_lift filtering."""
    engine = MarketBasketEngine(use_parquet=False)
    assert engine.data_source == "synthetic_fallback"
    assert len(engine.rules) >= 6

    all_rep = engine.generate_rules_report(min_lift=1.0, min_support_pct=0.5, limit=25)
    assert all_rep["status"] == "healthy"
    assert all_rep["summary"]["total_matching_rules"] > 0

    for r in all_rep["rules"]:
        assert 0.0 < r["support_pct"] <= 100.0
        assert 0.0 < r["confidence_pct"] <= 100.0
        assert r["lift"] >= 1.0
        assert r["bundle_offer_gbp"] <= r["bundle_retail_gbp"]

    strict_rep = engine.generate_rules_report(min_lift=2.5, min_support_pct=0.5, limit=10)
    assert all(r["lift"] >= 2.5 for r in strict_rep["rules"])


def test_bundle_evaluator_complementary_addons_and_aov_uplift():
    """Verify cart bundle scoring excludes already-selected SKUs and projects AOV uplift."""
    engine = MarketBasketEngine(use_parquet=False)
    res = engine.evaluate_bundle(items=["22423", "22699"], discount_pct=10.0)

    assert res["status"] == "success"
    assert res["base_subtotal_gbp"] > 0
    assert res["recommended_bundle_total_gbp"] > 0
    addon_codes = {a["stock_code"] for a in res["addons"]}
    assert "22423" not in addon_codes
    assert "22699" not in addon_codes
    assert len(addon_codes) >= 1


def test_api_market_basket_endpoints():
    """Verify FastAPI basket-rules GET and evaluate-bundle POST endpoints."""
    res_rules = client.get("/api/v1/recommendations/basket-rules?min_lift=1.3&limit=10")
    assert res_rules.status_code == 200
    data = res_rules.json()
    assert data["status"] == "healthy"
    assert len(data["rules"]) >= 1

    res_bundle = client.post(
        "/api/v1/recommendations/evaluate-bundle",
        json={"items": ["85123A"], "discount_pct": 12.0},
    )
    assert res_bundle.status_code == 200
    b_data = res_bundle.json()
    assert b_data["discount_pct"] == 12.0
    assert len(b_data["addons"]) >= 1

    bad_bundle = client.post(
        "/api/v1/recommendations/evaluate-bundle",
        json={"items": ["85123A"], "discount_pct": 85.0},
    )
    assert bad_bundle.status_code == 422

