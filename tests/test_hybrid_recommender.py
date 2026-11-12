"""
Unit & Integration Test Suite for Hybrid SVD Recommender & Next-Best-SKU Engine (Phase 31).
"""

from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.models.recommender import (
    ProductRecommender,
    get_product_recommender,
    categorize_product_desc,
    OBJECTIVE_WEIGHTS,
)
from src.api.server import app

client = TestClient(app)


def test_categorize_product_desc_and_margin_calibration():
    """Verify merchandise categorization rules and calibrated gross margins."""
    cat, margin = categorize_product_desc("REGENCY CAKESTAND 3 TIER")
    assert cat == "Kitchen & Dining"
    assert margin == 0.45

    cat, margin = categorize_product_desc("WHITE HANGING HEART T-LIGHT HOLDER")
    assert cat == "Home Decor & Lighting"
    assert margin == 0.50

    cat, margin = categorize_product_desc("PARTY BUNTING CELEBRATION")
    assert cat == "Party & Seasonal"
    assert margin == 0.55

    cat, margin = categorize_product_desc("JUMBO BAG RED RETROSPOT")
    assert cat == "Bags & Storage"
    assert margin == 0.48

    cat, margin = categorize_product_desc("WOODEN ASSORTED STAMP")
    assert cat == "Gifts & General Merchandise"
    assert margin == 0.42


def test_svd_matrix_factorization_architecture():
    """Assert TruncatedSVD components, user/item latent dimensions, and positive explained variance."""
    rec = get_product_recommender()
    diag = rec.get_diagnostics()

    assert diag["status"] == "healthy"
    assert diag["svd_latent_dimensions"] == 20
    assert diag["explained_variance_pct"] > 15.0
    assert diag["catalog_skus_indexed"] > 2000
    assert diag["customer_profiles_indexed"] > 3000
    assert set(diag["supported_objectives"]) == set(OBJECTIVE_WEIGHTS.keys())
    assert rec.user_factors.shape[1] == 20
    assert rec.item_factors.shape[0] == 20


def test_hybrid_next_best_sku_objectives():
    """Assert recommendations differ sensibly between balanced, margin_max, and discovery objectives."""
    rec = get_product_recommender()
    cid = "17850"

    bal_recs = rec.recommend_next_best_skus(customer_id=cid, top_n=5, objective="balanced")
    margin_recs = rec.recommend_next_best_skus(customer_id=cid, top_n=5, objective="margin_max")
    disc_recs = rec.recommend_next_best_skus(customer_id=cid, top_n=5, objective="discovery")

    assert len(bal_recs) == 5
    assert len(margin_recs) == 5
    assert len(disc_recs) == 5

    # Margin-Max should yield higher average unit margin than balanced
    avg_bal_margin = sum(r["EstimatedUnitMarginGBP"] for r in bal_recs) / 5.0
    avg_max_margin = sum(r["EstimatedUnitMarginGBP"] for r in margin_recs) / 5.0
    assert avg_max_margin > avg_bal_margin

    for r in bal_recs:
        assert "Rank" in r
        assert "StockCode" in r
        assert "UnitPriceINR" in r
        assert "HybridScore" in r
        assert "ExplanationBadge" in r


def test_cold_start_fallback_diversification():
    """Assert cold start fallback produces multi-category staples for unknown customer."""
    rec = get_product_recommender()
    cold_recs = rec.recommend_next_best_skus(customer_id="99999", top_n=5, objective="balanced")

    assert len(cold_recs) == 5
    categories = {r["Category"] for r in cold_recs}
    assert len(categories) >= 3  # Ensures diversification across catalog categories


def test_real_time_basket_recommendations():
    """Assert scoring an active cart returns complementary items with projected margin lift."""
    rec = get_product_recommender()
    cart = ["22423", "85123A"]

    basket_res = rec.recommend_for_basket(
        current_cart_skus=cart,
        customer_id="17850",
        top_n=4,
        objective="balanced",
    )

    assert basket_res["cart_item_count"] == 2
    assert basket_res["cart_subtotal_inr"] > 0
    assert basket_res["projected_top2_margin_lift_inr"] > 0
    assert len(basket_res["recommendations"]) == 4

    # Cart SKUs should not be recommended again
    rec_skus = {r["StockCode"] for r in basket_res["recommendations"]}
    assert "22423" not in rec_skus
    assert "85123A" not in rec_skus


def test_score_explanation_breakdown():
    """Assert explain_recommendation returns detailed factor attribution."""
    rec = get_product_recommender()
    exp = rec.explain_recommendation(customer_id="17850", stock_code="22469")

    assert exp["customer_id"] == "17850"
    assert exp["stock_code"] == "22469"
    assert "score_breakdown" in exp
    bd = exp["score_breakdown"]
    assert "svd_latent_affinity" in bd
    assert "collaborative_cross_sell" in bd
    assert "margin_contribution" in bd
    assert "category_affinity" in bd
    assert exp["badge"] != ""


def test_api_recommend_customer_endpoint():
    """Assert GET /api/v1/recommend/customer/{customer_id} returns valid payload."""
    res = client.get("/api/v1/recommend/customer/17850?top_n=4&objective=balanced")
    assert res.status_code == 200
    data = res.json()
    assert data["customer_id"] == "17850"
    assert data["objective"] == "balanced"
    assert data["is_cold_start"] is False
    assert len(data["recommendations"]) == 4


def test_api_recommend_next_best_sku_basket_endpoint():
    """Assert POST /api/v1/recommend/next-best-sku processes basket additions."""
    payload = {
        "customer_id": "14096",
        "current_cart_skus": ["22423"],
        "objective": "margin_max",
        "top_n": 3,
    }
    res = client.post("/api/v1/recommend/next-best-sku", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["cart_skus"] == ["22423"]
    assert data["objective_used"] == "margin_max"
    assert len(data["recommendations"]) == 3
    assert data["projected_top2_margin_lift_inr"] > 0


def test_api_recommend_explain_endpoint():
    """Assert GET /api/v1/recommend/explain/{customer_id}/{stock_code} returns breakdown."""
    res = client.get("/api/v1/recommend/explain/17850/22469?objective=balanced")
    assert res.status_code == 200
    data = res.json()
    assert data["customer_id"] == "17850"
    assert data["stock_code"] == "22469"
    assert "score_breakdown" in data


def test_api_recommend_stats_endpoint():
    """Assert GET /api/v1/recommend/stats returns system architecture metrics."""
    res = client.get("/api/v1/recommend/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["svd_latent_dimensions"] == 20
    assert data["explained_variance_pct"] > 10.0

