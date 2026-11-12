"""
Verification Suite for Phase 17: AI Inventory & Supply Chain Optimization Engine.

Covers:
1. InventoryOptimizationEngine synthetic fallback & ABC-XYZ Pareto assignment.
2. Mathematical monotonicity of Safety Stock, Reorder Point (ROP), and Wilson EOQ.
3. 30-day inventory depletion & sawtooth EOQ replenishment trajectory.
4. FastAPI REST endpoints (/inventory/optimization-report, /simulate-sku, /purchase-orders, /skus).
5. Enterprise RBAC enforcement ensuring only supply/admin roles can dispatch POs or mutate SKUs.
"""

from fastapi.testclient import TestClient

from src.api.security import SecurityRegistry
from src.api.server import app
from src.models.inventory_optimization import InventoryOptimizationEngine

client = TestClient(app)


def _login_as(email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_inventory_engine_synthetic_fallback_and_abc_xyz():
    """Verify deterministic fallback catalog initialization and ABC-XYZ segmentation."""
    engine = InventoryOptimizationEngine(use_parquet=False)
    assert engine.data_source == "synthetic_fallback"
    assert len(engine.skus) >= 10
    assert "22423" in engine.skus

    report = engine.generate_optimization_report()
    assert report["status"] == "healthy"
    assert report["kpis"]["active_skus_monitored"] == len(engine.skus)
    assert report["kpis"]["annual_eoq_savings_gbp"] > 0

    for row in report["skus"]:
        assert row["abc_class"] in ("A", "B", "C")
        assert row["xyz_class"] in ("X", "Y", "Z")
        assert row["eoq"] >= 10
        assert row["reorder_point"] > row["safety_stock"]


def test_eoq_safety_stock_and_rop_mathematical_monotonicity():
    """Verify higher service levels and longer lead times increase safety stock & ROP."""
    engine = InventoryOptimizationEngine(use_parquet=False)
    sku = engine.skus["22423"]

    low_sl = engine.compute_sku_policy(sku, service_level=0.90, lead_time_days=7)
    high_sl = engine.compute_sku_policy(sku, service_level=0.99, lead_time_days=7)
    assert high_sl["safety_stock"] > low_sl["safety_stock"]
    assert high_sl["reorder_point"] > low_sl["reorder_point"]
    assert high_sl["eoq"] == low_sl["eoq"]

    short_lt = engine.compute_sku_policy(sku, service_level=0.95, lead_time_days=3)
    long_lt = engine.compute_sku_policy(sku, service_level=0.95, lead_time_days=14)
    assert long_lt["safety_stock"] > short_lt["safety_stock"]
    assert long_lt["reorder_point"] > short_lt["reorder_point"]

    base_dem = engine.compute_sku_policy(sku, demand_multiplier=1.0)
    surge_dem = engine.compute_sku_policy(sku, demand_multiplier=2.0)
    assert surge_dem["eoq"] > base_dem["eoq"]


def test_sku_sawtooth_replenishment_simulation():
    """Verify 30-day depletion trajectory triggers EOQ replenishment when hitting ROP."""
    engine = InventoryOptimizationEngine(use_parquet=False)
    sim = engine.simulate_sku("22423", service_level=0.95, lead_time_days=5, horizon_days=30)

    traj = sim["trajectory"]
    assert len(traj) == 31
    assert traj[0]["day"] == 0
    assert traj[-1]["day"] == 30
    assert traj[-1]["eoq_managed_stock"] >= traj[-1]["unmanaged_stock"]


def test_api_inventory_optimization_and_simulation_endpoints():
    """Verify GET optimization report and POST simulate-sku endpoints."""
    rep = client.get("/api/v1/inventory/optimization-report?service_level=0.98&lead_time_days=10")
    assert rep.status_code == 200
    data = rep.json()
    assert data["parameters"]["service_level"] == 0.98
    assert data["parameters"]["lead_time_days"] == 10
    assert len(data["skus"]) >= 10

    sim = client.post(
        "/api/v1/inventory/simulate-sku",
        json={"stock_code": "85123A", "service_level": 0.95, "lead_time_days": 7, "demand_multiplier": 1.3},
    )
    assert sim.status_code == 200
    sim_data = sim.json()
    assert sim_data["policy"]["stock_code"] == "85123A"
    assert len(sim_data["trajectory"]) == 31

    missing = client.post(
        "/api/v1/inventory/simulate-sku",
        json={"stock_code": "DOES_NOT_EXIST"},
    )
    assert missing.status_code == 404


def test_api_purchase_order_and_sku_mutations_with_strict_rbac():
    """Verify PO issuance, SKU addition, and strict RBAC 403/200 enforcement."""
    growth_token = _login_as("growth@nexusretail.ai", "NexusGrowth2026!")
    supply_token = _login_as("supply@nexusretail.ai", "NexusOps2026!")

    SecurityRegistry().strict_rbac_enabled = True
    try:
        # Anonymous blocked (401)
        anon = client.post("/api/v1/inventory/purchase-orders", json={"stock_code": "22423", "order_qty": 100})
        assert anon.status_code == 401

        # Growth lacks inventory:write (403)
        deny_growth = client.post(
            "/api/v1/inventory/purchase-orders",
            headers={"Authorization": f"Bearer {growth_token}"},
            json={"stock_code": "22423", "order_qty": 100},
        )
        assert deny_growth.status_code == 403

        # Supply VP succeeds in issuing a PO
        before_rep = client.get("/api/v1/inventory/optimization-report").json()
        before_row = next(r for r in before_rep["skus"] if r["stock_code"] == "22699")
        before_stock = before_row["stock_on_hand"]

        po_res = client.post(
            "/api/v1/inventory/purchase-orders",
            headers={"Authorization": f"Bearer {supply_token}"},
            json={"stock_code": "22699", "order_qty": 250, "lead_time_days": 5},
        )
        assert po_res.status_code == 200, po_res.text
        po_payload = po_res.json()
        assert po_payload["purchase_order"]["po_id"].startswith("PO-")
        assert po_payload["updated_policy"]["stock_on_hand"] == before_stock + 250

        # Supply VP succeeds in registering a new catalog SKU
        sku_res = client.post(
            "/api/v1/inventory/skus",
            headers={"Authorization": f"Bearer {supply_token}"},
            json={
                "stock_code": "TEST999",
                "description": "Glass Carafe Limited",
                "unit_price": 14.5,
                "daily_demand_mean": 18.0,
                "stock_on_hand": 320,
            },
        )
        assert sku_res.status_code == 201, sku_res.text
        assert sku_res.json()["policy"]["stock_code"] == "TEST999"
    finally:
        SecurityRegistry().strict_rbac_enabled = False
