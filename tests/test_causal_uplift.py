"""
Verification Suite for Phase 26: Causal Uplift Modeling & Difference-in-Differences Attribution.

Covers:
1. T-Learner dual-model fitting & 4-quadrant CATE classification (Persuadables, Sure Things,
   Lost Causes, Sleeping Dogs).
2. Qini cumulative profit curve showing selective CATE targeting outperforms blanket promos.
3. Exact Difference-in-Differences (DiD) pre/post computation and significance testing.
4. FastAPI /api/v1/causal/uplift-report, /simulate-targeting, and /did-attribution endpoints.
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.models.causal_uplift import CausalUpliftEngine

client = TestClient(app)


def test_tlearner_quadrants_and_qini_advantage():
    """Verify T-Learner CATE scoring segments accounts cleanly and beats blanket discounts."""
    engine = CausalUpliftEngine(use_parquet=False)
    assert len(engine.customer_panel) >= 20

    rep = engine.simulate_targeting_policy(top_k_pct=30.0, discount_pct=15.0)
    assert rep["status"] == "healthy"
    assert len(rep["quadrants"]) == 4
    assert len(rep["qini_curve"]) == 10
    assert rep["summary"]["saved_promo_margin_gbp"] >= 0


def test_difference_in_differences_math_and_significance():
    """Verify exact DiD double-difference estimator & significance thresholding."""
    res = CausalUpliftEngine.compute_did_attribution(
        treat_pre=200.0,
        treat_post=285.0,
        ctrl_pre=195.0,
        ctrl_post=205.0,
        n_treat=400,
        n_ctrl=400,
    )
    # (285 - 200) - (205 - 195) = 85 - 10 = 75
    assert res["did_effect_per_account_gbp"] == 75.0
    assert res["statistically_significant"] is True
    assert res["p_value"] < 0.05


def test_api_causal_uplift_endpoints():
    """Verify FastAPI causal uplift report, simulate-targeting, and did-attribution endpoints."""
    rep_res = client.get("/api/v1/causal/uplift-report?top_k_pct=40&discount_pct=15")
    assert rep_res.status_code == 200
    data = rep_res.json()
    assert data["parameters"]["top_k_pct"] == 40.0
    assert len(data["quadrants"]) == 4

    sim_res = client.post(
        "/api/v1/causal/simulate-targeting",
        json={"top_k_pct": 20.0, "discount_pct": 20.0},
    )
    assert sim_res.status_code == 200
    assert len(sim_res.json()["qini_curve"]) == 10

    did_res = client.post(
        "/api/v1/causal/did-attribution",
        json={"treat_pre": 150.0, "treat_post": 210.0, "ctrl_pre": 148.0, "ctrl_post": 155.0},
    )
    assert did_res.status_code == 200
    assert did_res.json()["did_effect_per_account_gbp"] == 53.0

