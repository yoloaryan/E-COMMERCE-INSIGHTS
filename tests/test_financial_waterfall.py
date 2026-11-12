"""
Verification Suite for Phase 22: Return & Refund Financial Waterfall + Unit Economics.

Covers:
1. Accounting reconciliation invariant: Gross GMV - Returns == Net Realized Revenue,
   and Net Revenue - COGS - Reverse Logistics == Net Contribution Margin.
2. Country unit economics & top return-prone SKU leakage attribution.
3. Monotonicity of Return-Reduction EBITDA/Margin Recovery simulator.
4. FastAPI /api/v1/finance/waterfall-report and /simulate-margin-recovery endpoints.
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.models.financial_waterfall import FinancialWaterfallEngine

client = TestClient(app)


def test_financial_waterfall_accounting_reconciliation():
    """Verify exact Gross-to-Net P&L identity and non-negative return leakage bounds."""
    engine = FinancialWaterfallEngine(use_parquet=False)
    assert engine.data_source == "synthetic_fallback"

    rep = engine.generate_waterfall_report(country="All", cogs_ratio=0.58)
    assert rep["status"] == "healthy"
    s = rep["summary"]

    assert s["gross_gmv_gbp"] > 0
    assert s["return_leakage_gbp"] > 0
    assert round(s["gross_gmv_gbp"] - s["return_leakage_gbp"], 2) == s["net_revenue_gbp"]
    expected_margin = round(s["net_revenue_gbp"] - s["cogs_estimate_gbp"] - s["reverse_logistics_gbp"], 2)
    assert expected_margin == s["net_contribution_margin_gbp"]
    assert len(rep["waterfall"]) == 5
    assert len(rep["country_margins"]) >= 4
    assert len(rep["high_return_skus"]) >= 1


def test_margin_recovery_simulation_monotonicity():
    """Verify higher return-reduction targets save strictly more net contribution margin."""
    engine = FinancialWaterfallEngine(use_parquet=False)
    low = engine.simulate_margin_recovery(return_reduction_pct=10.0)
    high = engine.simulate_margin_recovery(return_reduction_pct=50.0)

    assert high["outputs"]["incremental_net_margin_gbp"] > low["outputs"]["incremental_net_margin_gbp"]
    assert high["outputs"]["target_return_rate_pct"] < low["outputs"]["target_return_rate_pct"]


def test_api_financial_waterfall_endpoints():
    """Verify FastAPI waterfall-report and simulate-margin-recovery endpoints."""
    rep_res = client.get("/api/v1/finance/waterfall-report?country=United%20Kingdom&cogs_ratio=0.55")
    assert rep_res.status_code == 200
    data = rep_res.json()
    assert data["filters"]["country"] == "United Kingdom"
    assert len(data["waterfall"]) == 5

    sim_res = client.post(
        "/api/v1/finance/simulate-margin-recovery",
        json={"return_reduction_pct": 30.0, "country": "All", "cogs_ratio": 0.58},
    )
    assert sim_res.status_code == 200
    assert sim_res.json()["outputs"]["incremental_net_margin_gbp"] > 0

    bad_sim = client.post(
        "/api/v1/finance/simulate-margin-recovery",
        json={"return_reduction_pct": 95.0},
    )
    assert bad_sim.status_code == 422
