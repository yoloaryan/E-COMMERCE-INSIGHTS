"""
Unit & Integration Tests for Phase 30: Split-Conformal Demand Uncertainty & KKT Budget Optimizer.
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.models.conformal_optimizer import ConformalOptimizerEngine

client = TestClient(app)


def test_split_conformal_ordering_and_coverage_monotonicity(tmp_path):
    engine = ConformalOptimizerEngine(forecast_path=tmp_path / "missing_forecast.csv")
    c80 = engine.compute_conformal_intervals(confidence_pct=80.0)
    c95 = engine.compute_conformal_intervals(confidence_pct=95.0)

    assert c80["status"] == "healthy"
    assert len(c80["series"]) == 60
    for pt in c80["series"]:
        assert 0.0 <= pt["lower_inr"] <= pt["point_p50_inr"] <= pt["upper_inr"]

    # Higher target confidence must yield wider or equal conformal bounds and multiplier q
    assert c95["summary"]["conformal_multiplier_q"] >= c80["summary"]["conformal_multiplier_q"]
    assert c95["summary"]["avg_interval_width_inr"] >= c80["summary"]["avg_interval_width_inr"]
    assert c80["summary"]["empirical_eval_coverage_pct"] >= 60.0


def test_kkt_budget_optimizer_conservation_and_equal_split_dominance(tmp_path):
    engine = ConformalOptimizerEngine(forecast_path=tmp_path / "missing_forecast.csv")
    res = engine.optimize_marketing_budget(total_budget_inr=250000.0, min_roi_multiple=1.5)
    s = res["summary"]

    assert abs((s["allocated_budget_inr"] + s["unallocated_reserve_inr"]) - s["total_budget_inr"]) < 1e-2
    assert s["optimizer_gain_over_equal_inr"] >= 0.0
    assert s["optimal_incremental_margin_inr"] >= s["equal_split_margin_inr"]

    # High CFO hurdle should naturally leave unallocated reserve instead of wasting budget below hurdle
    strict = engine.optimize_marketing_budget(total_budget_inr=1000000.0, min_roi_multiple=3.5)
    assert strict["summary"]["unallocated_reserve_inr"] > 0.0
    for row in strict["allocations"]:
        if row["allocated_budget_inr"] > 0:
            assert row["marginal_roas_x"] >= 3.45


def test_api_conformal_and_budget_optimizer_endpoints():
    r1 = client.get("/api/v1/forecast/conformal-intervals?confidence_pct=90")
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["status"] == "healthy"
    assert b1["summary"]["target_confidence_pct"] == 90.0

    r2 = client.post(
        "/api/v1/campaigns/optimize-budget",
        json={"total_budget_inr": 300000.0, "min_roi_multiple": 1.6},
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["status"] == "healthy"
    assert len(b2["allocations"]) == 4
    assert b2["summary"]["portfolio_roas_x"] > 1.0
