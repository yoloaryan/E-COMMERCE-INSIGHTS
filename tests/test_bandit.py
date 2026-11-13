"""
Unit and Integration Tests for Phase 33: Multi-Armed Bandit (MAB) Reinforcement Learning Engine.
Verifies Thompson Sampling, UCB-1, Disjoint Contextual LinUCB, Regret Minimization, and FastAPI endpoints.
"""

from fastapi.testclient import TestClient
import numpy as np
import pytest

from src.models.bandit import MultiArmedBanditEngine, BanditArm, DEFAULT_PRICING_ARMS
from src.api.server import app

client = TestClient(app)


def test_bandit_arm_data_structure_and_credible_interval():
    arm = BanditArm(
        arm_id="test_arm",
        label="Test 10% Discount",
        price_multiplier=0.90,
        true_conversion_rate=0.20,
        base_unit_price=1000.0,
    )
    assert arm.unit_price == 900.0
    assert arm.alpha == 1.0
    assert arm.beta == 1.0
    assert arm.mean_conversion_rate == 0.50  # 1 / (1 + 1)

    # 95% Credible Interval on Uniform prior Beta(1,1) is approximately [0.025, 0.975]
    lo, hi = arm.credible_interval(confidence=0.95)
    assert 0.02 <= lo <= 0.03
    assert 0.97 <= hi <= 0.98

    # Simulate 20 successes and 80 failures => Beta(21, 81)
    arm.alpha = 21.0
    arm.beta = 81.0
    lo2, hi2 = arm.credible_interval(confidence=0.95)
    mean2 = arm.mean_conversion_rate
    assert 0.19 <= mean2 <= 0.22
    assert lo2 < mean2 < hi2
    assert hi2 - lo2 < 0.20  # Interval narrow with 100 observations

    d = arm.to_dict()
    assert d["arm_id"] == "test_arm"
    assert d["unit_price_inr"] == 900.0
    assert d["credible_interval_95"] == [lo2, hi2]


def test_thompson_sampling_and_ucb1_selection_invariants():
    engine = MultiArmedBanditEngine(base_unit_price=1200.0, seed=42)
    assert len(engine.arms) == len(DEFAULT_PRICING_ARMS)

    # 1. Thompson Sampling selection
    t_decision = engine.select_arm(strategy="thompson")
    assert t_decision["selected_arm_id"] in engine.arms
    assert t_decision["offered_price_inr"] > 0
    assert t_decision["strategy_used"] == "thompson"
    assert "scores_by_arm" in t_decision
    assert len(t_decision["scores_by_arm"]) == 5

    # 2. UCB-1 initialization: unpulled arms must be pulled first
    ucb_decision = engine.select_arm(strategy="ucb1")
    assert ucb_decision["selected_arm_id"] in engine.arms
    assert ucb_decision["strategy_used"] == "ucb1"
    assert ucb_decision["is_exploration"] is True

    # 3. Contextual LinUCB selection
    ctx = [1.0, 0.85, 0.90, 0.50]  # High spend, frequent customer
    lin_decision = engine.select_arm(strategy="linucb", context=ctx)
    assert lin_decision["selected_arm_id"] in engine.arms
    assert lin_decision["strategy_used"] == "linucb"
    assert len(lin_decision["customer_context"]) == 4

    # 4. Epsilon-Greedy selection
    eps_decision = engine.select_arm(strategy="epsilon_greedy", exploration_factor=0.0)
    assert eps_decision["strategy_used"] == "epsilon_greedy"
    assert eps_decision["is_exploration"] is False


def test_bayesian_reward_update_and_posterior_shift():
    engine = MultiArmedBanditEngine(base_unit_price=1000.0, seed=42)
    arm_id = "volume_10"
    init_alpha = engine.arms[arm_id].alpha
    init_beta = engine.arms[arm_id].beta

    # Record 5 conversions on volume_10
    for _ in range(5):
        res = engine.record_reward(arm_id=arm_id, converted=True, revenue=900.0)

    assert res["alpha"] == init_alpha + 5.0
    assert res["conversion_count"] == 5
    assert res["total_arm_revenue_inr"] == 4500.0
    assert engine.arms[arm_id].mean_conversion_rate > 0.5

    # Record 5 failures on full_price
    arm2 = "full_price"
    for _ in range(5):
        res2 = engine.record_reward(arm_id=arm2, converted=False, revenue=0.0)

    assert res2["beta"] == init_beta + 5.0
    assert res2["conversion_count"] == 0
    assert engine.arms[arm2].mean_conversion_rate < 0.5


def test_bandit_simulation_regret_minimization_and_oracle_comparison():
    engine = MultiArmedBanditEngine(base_unit_price=1250.0, seed=123)
    sim = engine.simulate(rounds=600, strategy="thompson", seed=123)

    assert sim["status"] == "completed"
    assert sim["rounds_simulated"] == 600
    assert len(sim["trajectory"]) >= 20
    assert sim["oracle_expected_revenue"] > 0

    # Key invariant: Total revenue of Oracle is highest, MAB achieves lower regret than A/B test
    assert sim["total_revenue_oracle_inr"] >= sim["total_revenue_mab_inr"]
    assert sim["cumulative_regret_mab_inr"] < sim["cumulative_regret_ab_inr"]
    assert sim["regret_saved_pct"] > 0.0

    # Trajectory check
    first_step = sim["trajectory"][0]
    last_step = sim["trajectory"][-1]
    assert last_step["cumulative_revenue_mab"] > first_step["cumulative_revenue_mab"]
    assert last_step["cumulative_regret_mab"] > first_step["cumulative_regret_mab"]
    assert len(last_step["arm_allocation_shares"]) == 5


def test_api_bandit_endpoints_via_testclient():
    # 1. GET /api/v1/bandit/arms
    res_arms = client.get("/api/v1/bandit/arms")
    assert res_arms.status_code == 200
    body_arms = res_arms.json()
    assert body_arms["status"] == "success"
    assert len(body_arms["arms"]) == 5

    # 2. POST /api/v1/bandit/select-arm
    res_sel = client.post(
        "/api/v1/bandit/select-arm",
        json={
            "strategy": "thompson",
            "customer_context": [1.0, 0.5, 0.7, 0.2],
            "exploration_factor": 1.0,
        },
    )
    assert res_sel.status_code == 200
    body_sel = res_sel.json()
    assert "selected_arm_id" in body_sel
    assert body_sel["offered_price_inr"] > 0

    # 3. POST /api/v1/bandit/reward
    arm_id = body_sel["selected_arm_id"]
    res_rew = client.post(
        "/api/v1/bandit/reward",
        json={
            "arm_id": arm_id,
            "converted": True,
            "revenue": 1125.0,
        },
    )
    assert res_rew.status_code == 200
    assert res_rew.json()["status"] == "success"
    assert res_rew.json()["conversion_count"] >= 1

    # 4. GET /api/v1/bandit/performance
    res_perf = client.get("/api/v1/bandit/performance")
    assert res_perf.status_code == 200
    perf = res_perf.json()["performance"]
    assert perf["total_rounds"] >= 1
    assert perf["total_revenue_inr"] >= 1125.0
    assert "cumulative_regret_inr" in perf

    # 5. POST /api/v1/bandit/simulate
    res_sim = client.post(
        "/api/v1/bandit/simulate",
        json={
            "rounds": 200,
            "strategy": "ucb1",
            "exploration_factor": 1.2,
            "seed": 999,
        },
    )
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data["rounds_simulated"] == 200
    assert sim_data["strategy"] == "ucb1"
    assert "regret_saved_pct" in sim_data

    # 6. POST /api/v1/bandit/reset
    res_reset = client.post("/api/v1/bandit/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "success"

