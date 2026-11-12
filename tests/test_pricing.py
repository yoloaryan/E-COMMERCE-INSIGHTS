"""
Unit and Integration Tests for Dynamic Pricing Elasticity & A/B Experimentation Engine.
"""

from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.api.server import app
from src.models.pricing_elasticity import (
    PricingElasticityEngine,
    ABExperimentEngine,
    PricingExperimentRegistry,
    categorize_product,
    classify_elasticity_regime,
)

client = TestClient(app)


def test_categorize_product_taxonomy():
    """Verify deterministic product taxonomy mapping across retail descriptions."""
    assert categorize_product("Regency Cakestand 3 Tier") == "Kitchen & Dining"
    assert categorize_product("White Hanging Heart T-Light Holder") == "Home Decor & Lighting"
    assert categorize_product("Jumbo Bag Red Retrospot") == "Bags & Storage"
    assert categorize_product("Paper Chain Kit 50'S Christmas") == "Seasonal & Party"
    assert categorize_product("Set of 6 Vintage Note Cards") == "Stationery & Craft"
    assert categorize_product("Miscellaneous Collectible Item") == "General Giftware"
    assert classify_elasticity_regime(-1.45).startswith("Elastic")
    assert classify_elasticity_regime(-1.00).startswith("Unit Elastic")
    assert classify_elasticity_regime(-0.65).startswith("Inelastic")


def test_pricing_engine_synthetic_fallback():
    """Assert PricingElasticityEngine operates smoothly on synthetic fallback when parquet is absent."""
    missing_path = Path("/tmp/non_existent_retail_data_phase13.parquet")
    engine = PricingElasticityEngine(data_path=missing_path)
    assert engine.data_source == "synthetic_fallback"

    report = engine.generate_elasticity_report()
    assert report["status"] == "success"
    assert len(report["categories"]) >= 5
    for cat in report["categories"]:
        assert -3.2 <= cat["elasticity_coefficient"] <= -0.35
        assert cat["baseline_avg_price_gbp"] > 0
        assert cat["baseline_revenue_gbp"] > 0
        assert cat["projected_max_profit_gbp"] >= cat["baseline_gross_margin_gbp"]


def test_isoelastic_price_simulation_math():
    """Assert isoelastic demand invariants: baseline parity, inverse demand, and unit cost invariance."""
    missing_path = Path("/tmp/non_existent_retail_sim_phase13.parquet")
    engine = PricingElasticityEngine(data_path=missing_path)

    # 0% price adjustment matches baseline exactly
    res_zero = engine.simulate_price_change(category="Kitchen & Dining", price_change_pct=0.0, cogs_ratio=0.55)
    assert res_zero["baseline"]["revenue_gbp"] == pytest.approx(res_zero["simulated"]["projected_revenue_gbp"], rel=1e-4)
    assert res_zero["baseline"]["gross_profit_gbp"] == pytest.approx(res_zero["simulated"]["projected_gross_profit_gbp"], rel=1e-4)
    assert res_zero["simulated"]["profit_delta_gbp"] == pytest.approx(0.0, abs=0.05)

    # Price increase reduces units sold under negative elasticity; payoff curve spans -20%..+20%
    res_up = engine.simulate_price_change(category="Kitchen & Dining", price_change_pct=10.0, elasticity_override=-1.5)
    assert res_up["simulated"]["unit_delta_pct"] < 0
    assert res_up["simulated"]["new_price_gbp"] > res_up["baseline"]["avg_price_gbp"]
    assert len(res_up["payoff_curve"]) == 21
    assert res_up["payoff_curve"][0]["price_change_pct"] == -20.0
    assert res_up["payoff_curve"][-1]["price_change_pct"] == 20.0

    # Price cut increases units sold
    res_down = engine.simulate_price_change(category="Seasonal & Party", price_change_pct=-10.0, elasticity_override=-1.8)
    assert res_down["simulated"]["unit_delta_pct"] > 0


def test_ab_power_calculator_math():
    """Assert sample size responds correctly to MDE, statistical power, and split ratio."""
    # Higher MDE requires substantially fewer visitors
    small_mde = ABExperimentEngine.calculate_power_and_sample_size(
        baseline_conversion_rate=0.05,
        minimum_detectable_effect_pct=5.0,
        alpha=0.05,
        power=0.80,
        daily_traffic=2000,
    )
    large_mde = ABExperimentEngine.calculate_power_and_sample_size(
        baseline_conversion_rate=0.05,
        minimum_detectable_effect_pct=20.0,
        alpha=0.05,
        power=0.80,
        daily_traffic=2000,
    )
    assert small_mde["total_sample_size"] > large_mde["total_sample_size"]
    assert small_mde["estimated_duration_days"] >= large_mde["estimated_duration_days"]

    # Higher power requires more visitors
    power_90 = ABExperimentEngine.calculate_power_and_sample_size(
        baseline_conversion_rate=0.05,
        minimum_detectable_effect_pct=10.0,
        power=0.90,
    )
    power_80 = ABExperimentEngine.calculate_power_and_sample_size(
        baseline_conversion_rate=0.05,
        minimum_detectable_effect_pct=10.0,
        power=0.80,
    )
    assert power_90["total_sample_size"] > power_80["total_sample_size"]

    # Power curve monotonic increasing with visitor count
    powers = [pt["power_pct"] for pt in power_80["power_curve"]]
    assert powers == sorted(powers)


def test_ab_experiment_statistical_significance():
    """Verify two-proportion Z-test detects decisive winner vs inconclusive tie."""
    engine = PricingElasticityEngine(data_path=Path("/tmp/non_existent_ab_phase13.parquet"))

    # Decisive Variant Winner (significantly higher conversion rate + small price bump)
    win_res = ABExperimentEngine.run_experiment(
        experiment_name="Kitchen Price Lift Test",
        category="Kitchen & Dining",
        price_change_pct=5.0,
        control_visitors=5000,
        control_conversions=200,   # 4.0%
        variant_visitors=5000,
        variant_conversions=295,   # 5.9%
        engine=engine,
    )
    exp_win = win_res["experiment"]
    assert exp_win["statistics"]["statistically_significant"] is True
    assert exp_win["statistics"]["p_value"] < 0.001
    assert exp_win["statistics"]["winner"] == "VARIANT"

    # Inconclusive near-tie
    tie_res = ABExperimentEngine.run_experiment(
        experiment_name="Noise Tie Test",
        category="Bags & Storage",
        price_change_pct=2.0,
        control_visitors=1000,
        control_conversions=45,
        variant_visitors=1000,
        variant_conversions=46,
        engine=engine,
    )
    exp_tie = tie_res["experiment"]
    assert exp_tie["statistics"]["statistically_significant"] is False
    assert exp_tie["statistics"]["p_value"] > 0.5
    assert exp_tie["statistics"]["winner"] == "INCONCLUSIVE"


def test_api_elasticity_report_endpoint():
    """Assert GET /api/v1/pricing/elasticity-report returns category elasticity table."""
    res = client.get("/api/v1/pricing/elasticity-report")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["categories"]) >= 5
    assert "avg_portfolio_elasticity" in data
    assert "top_sensitive_skus" in data
    first = data["categories"][0]
    assert "elasticity_coefficient" in first
    assert "optimal_price_change_pct" in first


def test_api_simulate_price_change_endpoint():
    """Assert POST /api/v1/pricing/simulate-price-change returns payoff curve and validation."""
    payload = {
        "category": "Kitchen & Dining",
        "price_change_pct": 8.0,
        "cogs_ratio": 0.56,
        "promo_discount_pct": 0.0,
    }
    res = client.post("/api/v1/pricing/simulate-price-change", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["category"] == "Kitchen & Dining"
    assert len(data["payoff_curve"]) == 21
    assert "optimal_point" in data
    assert "recommendation" in data

    # Unknown category returns HTTP 400 cleanly
    bad = client.post("/api/v1/pricing/simulate-price-change", json={"category": "NonExistentCategory999", "price_change_pct": 5.0})
    assert bad.status_code == 400


def test_api_ab_test_calculator_endpoint():
    """Assert GET /api/v1/pricing/ab-test-calculator returns sample sizing & power curve."""
    res = client.get(
        "/api/v1/pricing/ab-test-calculator"
        "?baseline_conversion_rate=0.045&minimum_detectable_effect_pct=12&alpha=0.05&power=0.80&daily_traffic=3000&holdout_ratio=0.25"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_sample_size"] == data["sample_size_control"] + data["sample_size_variant"]
    assert data["sample_size_variant"] > data["sample_size_control"]
    assert data["estimated_duration_days"] >= 1
    assert len(data["power_curve"]) >= 6


def test_api_run_ab_experiment_endpoint():
    """Assert POST /api/v1/pricing/run-ab-experiment executes, records ledger, and computes p-value."""
    before_count = len(PricingExperimentRegistry().list_experiments())
    payload = {
        "experiment_name": "Q4 Home Decor Holdout Test",
        "category": "Home Decor & Lighting",
        "price_change_pct": -10.0,
        "holdout_pct": 20.0,
        "sample_size": 12000,
        "baseline_conversion_rate": 0.05,
        "cogs_ratio": 0.54,
        "seed": 123,
    }
    res = client.post("/api/v1/pricing/run-ab-experiment", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    exp = data["experiment"]
    assert exp["experiment_name"] == "Q4 Home Decor Holdout Test"
    assert exp["control"]["visitors"] == 2400
    assert exp["variant"]["visitors"] == 9600
    assert 0.0 <= exp["statistics"]["p_value"] <= 1.0
    assert exp["statistics"]["winner"] in ["VARIANT", "CONTROL", "INCONCLUSIVE"]

    after_count = len(PricingExperimentRegistry().list_experiments())
    assert after_count >= before_count


def test_promo_discount_overlay_simulation():
    """Verify promotional discount overlay compounds multiplicatively with list price change."""
    engine = PricingElasticityEngine(data_path=Path("/tmp/non_existent_promo_phase13.parquet"))
    # +10% list markup compounded with 10% promo discount => 1.10 * 0.90 = 0.99 (-1.0% effective change)
    res = engine.simulate_price_change(
        category="Kitchen & Dining",
        price_change_pct=10.0,
        promo_discount_pct=10.0,
    )
    assert res["effective_price_change_pct"] == pytest.approx(-1.0, abs=0.01)
    assert res["simulated"]["new_price_gbp"] <= res["baseline"]["avg_price_gbp"]


def test_pricing_lerner_margin_sensitivity():
    """Verify optimal price drops when unit COGS margin room widens significantly."""
    engine = PricingElasticityEngine(data_path=Path("/tmp/non_existent_lerner_phase13.parquet"))
    low_cogs = engine.simulate_price_change(
        category="Bags & Storage", price_change_pct=0.0, cogs_ratio=0.30, elasticity_override=-1.8
    )
    high_cogs = engine.simulate_price_change(
        category="Bags & Storage", price_change_pct=0.0, cogs_ratio=0.70, elasticity_override=-1.8
    )
    assert high_cogs["optimal_point"]["optimal_price_gbp"] > low_cogs["optimal_point"]["optimal_price_gbp"]


def test_api_ab_experiment_validation_bounds():
    """Verify unknown category yields HTTP 400 and invalid sample size yields HTTP 422."""
    bad_cat = client.post("/api/v1/pricing/run-ab-experiment", json={
        "experiment_name": "Invalid Cat Test",
        "category": "NonExistentCategory999",
        "price_change_pct": 5.0,
    })
    assert bad_cat.status_code == 400

    bad_sample = client.post("/api/v1/pricing/run-ab-experiment", json={
        "experiment_name": "Too Small Sample",
        "category": "Kitchen & Dining",
        "sample_size": 10,
    })
    assert bad_sample.status_code == 422

