"""
Unit & Integration Tests for Phase 27: Survival Analysis, Weibull Hazard Modeling & Exact Shapley XAI.
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.models.survival_xai import SurvivalXAIEngine, _generate_synthetic_survival_df

client = TestClient(app)


def test_kaplan_meier_monotonicity_and_greenwood_ci(tmp_path):
    # Exercise synthetic fallback cleanly without depending on processed CSV
    missing_csv = tmp_path / "nonexistent_churn.csv"
    engine = SurvivalXAIEngine(data_path=missing_csv)
    report = engine.get_kaplan_meier_report(segment="All")

    assert report["status"] == "healthy"
    assert report["summary"]["total_accounts"] == 480

    cohorts = report["cohorts"]
    for name in ["All", "Champions (VIP)", "Loyal Customers", "At-Risk / Lapsing", "Occasional / Hibernating"]:
        km = cohorts[name]
        curve = km["curve"]
        assert curve[0]["day"] == 0
        assert curve[0]["survival"] == 1.0
        for idx, pt in enumerate(curve):
            assert 0.0 <= pt["ci_lower"] <= pt["survival"] <= pt["ci_upper"] <= 1.0
            if idx > 0:
                assert pt["survival"] <= curve[idx - 1]["survival"] + 1e-9

    assert cohorts["Champions (VIP)"]["s_90"] > cohorts["Occasional / Hibernating"]["s_90"]
    assert cohorts["Champions (VIP)"]["rmst_365"] > cohorts["Occasional / Hibernating"]["rmst_365"]


def test_exact_coalitional_shapley_and_counterfactual_lift(tmp_path):
    missing_csv = tmp_path / "nonexistent_churn.csv"
    engine = SurvivalXAIEngine(data_path=missing_csv)

    xai = engine.explain_customer("14096")
    assert xai["customer_id"] == "14096"
    rs = xai["risk_summary"]
    # Verify exact Shapley efficiency property: base + sum(phi) == prediction
    assert rs["efficiency_error_pp"] < 1e-2
    assert len(xai["contributions"]) == 6

    wb = xai["weibull"]
    assert 1.0 >= wb["survival_30d"] >= wb["survival_90d"] >= wb["survival_180d"] >= 0.0

    cf = engine.simulate_retention_intervention(
        customer_id="14096",
        recency_reduction_days=60,
        frequency_boost_orders=3,
        aov_boost_pct=20.0,
    )
    sum_cf = cf["summary"]
    assert sum_cf["delta_s90_pp"] > 0.0
    assert sum_cf["rmst_gain_days"] > 0.0
    assert sum_cf["protected_margin_gbp"] > 0.0
    assert len(cf["comparison_curve"]) == 13


def test_api_survival_xai_endpoints():
    res_km = client.get("/api/v1/survival/kaplan-meier-report?segment=Champions%20(VIP)")
    assert res_km.status_code == 200
    body_km = res_km.json()
    assert body_km["status"] == "healthy"
    assert "Champions (VIP)" in body_km["cohorts"]
    assert len(body_km["global_importance"]) == 6

    res_xai = client.get("/api/v1/survival/explain/14096")
    assert res_xai.status_code == 200
    body_xai = res_xai.json()
    assert body_xai["customer_id"] == "14096"
    assert body_xai["risk_summary"]["efficiency_error_pp"] < 1e-2

    res_cf = client.post(
        "/api/v1/survival/simulate-intervention",
        json={
            "customer_id": "12352",
            "recency_reduction_days": 50,
            "frequency_boost_orders": 2,
            "aov_boost_pct": 15.0,
        },
    )
    assert res_cf.status_code == 200
    body_cf = res_cf.json()
    assert body_cf["customer_id"] == "12352"
    assert body_cf["summary"]["delta_s90_pp"] > 0.0

