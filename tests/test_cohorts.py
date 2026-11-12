"""
Verification Suite for Phase 18: Cohort Retention Heatmap & RFM Segment Migration Engine.

Covers:
1. CohortAnalyticsEngine synthetic fallback & M0=100% acquisition baseline invariant.
2. Customer logo retention (%) vs Net Revenue Retention (NRR %) matrix computation.
3. Prior H1 -> Current H2 4x4 RFM Markov transition matrix probability conservation.
4. Monotonicity of What-If Retention & Win-Back LTV Lift simulation.
5. FastAPI REST endpoints (/cohorts/retention-report, /segment-migration, /simulate-lift).
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.models.cohort_analytics import CohortAnalyticsEngine, SEGMENT_ORDER

client = TestClient(app)


def test_cohort_engine_retention_invariants():
    """Verify M0=100.0% baseline and bounded logo retention curves on synthetic corpus."""
    engine = CohortAnalyticsEngine(use_parquet=False)
    assert engine.data_source == "synthetic_fallback"

    rep = engine.generate_retention_report(metric="customers", country="All")
    assert rep["status"] == "success"
    assert len(rep["cohorts"]) == 13
    assert len(rep["month_headers"]) == 13

    for row in rep["cohorts"]:
        pcts = row["customer_retention_pcts"]
        assert pcts[0] == 100.0
        observed = [p for p in pcts if p is not None]
        assert all(0.0 <= p <= 100.0 for p in observed)

    rev_rep = engine.generate_retention_report(metric="revenue", country="Germany")
    assert rev_rep["metric"] == "revenue"
    assert rev_rep["cohorts"][0]["revenue_retention_pcts"][0] == 100.0


def test_rfm_markov_segment_migration_conservation():
    """Verify 4x4 transition rows conserve 100% probability mass across observed accounts."""
    engine = CohortAnalyticsEngine(use_parquet=False)
    mig = engine.generate_migration_report()

    assert mig["segments"] == SEGMENT_ORDER
    assert mig["summary"]["tracked_prior_accounts"] > 0

    for row in mig["matrix"]:
        total_pct = sum(row["transitions"][dst]["pct"] for dst in SEGMENT_ORDER)
        if row["total_accounts"] > 0:
            assert 99.0 <= total_pct <= 101.0


def test_retention_lift_simulation_monotonicity():
    """Verify higher Month-1 repeat lift and win-back rate produce higher revenue yield."""
    engine = CohortAnalyticsEngine(use_parquet=False)
    low = engine.simulate_retention_lift(month1_lift_pp=2.0, winback_recovery_pct=10.0)
    high = engine.simulate_retention_lift(month1_lift_pp=12.0, winback_recovery_pct=40.0)

    assert high["outputs"]["projected_month1_retention_pct"] > low["outputs"]["projected_month1_retention_pct"]
    assert high["outputs"]["total_annual_revenue_lift_gbp"] > low["outputs"]["total_annual_revenue_lift_gbp"]


def test_api_cohort_and_migration_endpoints():
    """Verify Phase 18 FastAPI endpoints return 200 and full structured payloads."""
    ret_res = client.get("/api/v1/cohorts/retention-report?metric=customers&country=All")
    assert ret_res.status_code == 200
    ret_data = ret_res.json()
    assert len(ret_data["cohorts"]) >= 6
    assert len(ret_data["average_curve"]["labels"]) == len(ret_data["month_headers"])

    mig_res = client.get("/api/v1/cohorts/segment-migration")
    assert mig_res.status_code == 200
    mig_data = mig_res.json()
    assert len(mig_data["matrix"]) == 4

    sim_res = client.post(
        "/api/v1/cohorts/simulate-lift",
        json={"month1_lift_pp": 7.5, "winback_recovery_pct": 25.0},
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["outputs"]["total_annual_revenue_lift_gbp"] > 0
