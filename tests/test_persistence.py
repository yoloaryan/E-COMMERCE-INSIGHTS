"""
Verification Suite for Phase 19: Persistent SQLite State Store & Storage Telemetry.

Covers:
1. SQLiteStateStore schema initialization, WAL mode, and checkpoint execution.
2. True simulated restart durability: POs & custom SKUs survive across separate engine instances.
3. Persistence round-trips for fraud alerts, audit events, tenants, campaigns, and channel configs.
4. FastAPI /api/v1/system/persistence-status and /persistence/checkpoint telemetry endpoints.
"""

from pathlib import Path
from fastapi.testclient import TestClient

from src.api.server import app
from src.models.inventory_optimization import InventoryOptimizationEngine
from src.utils.state_store import SQLiteStateStore

client = TestClient(app)


def test_sqlite_state_store_restart_durability_for_inventory(tmp_path: Path):
    """Verify Purchase Orders and Custom SKUs persist across fresh engine instantiations."""
    db_file = tmp_path / "durable_restart.db"

    store_1 = SQLiteStateStore(db_path=db_file)
    engine_1 = InventoryOptimizationEngine(use_parquet=False, state_store=store_1)
    engine_1.add_sku(
        stock_code="PERSIST01",
        description="Handcrafted Ceramic Carafe",
        unit_price=19.99,
        daily_demand_mean=12.0,
        stock_on_hand=150,
    )
    po_res = engine_1.issue_purchase_order(stock_code="PERSIST01", order_qty=300, actor_email="supply@nexusretail.ai")
    po_id = po_res["purchase_order"]["po_id"]
    assert po_res["updated_policy"]["stock_on_hand"] == 450

    # Simulate cold server restart by creating a new store and engine pointing at the same SQLite file
    store_2 = SQLiteStateStore(db_path=db_file)
    engine_2 = InventoryOptimizationEngine(use_parquet=False, state_store=store_2)
    assert "PERSIST01" in engine_2.skus
    assert engine_2.skus["PERSIST01"]["stock_on_hand"] == 450
    assert any(po["po_id"] == po_id for po in engine_2.purchase_orders)


def test_sqlite_state_store_roundtrips_all_operational_tables(tmp_path: Path):
    """Verify fraud alerts, audit stream, tenants, campaigns, and channel configs persist on disk."""
    db_file = tmp_path / "all_tables.db"
    store = SQLiteStateStore(db_path=db_file)

    store.save_fraud_alert({"alert_id": "FRD-9991", "status": "BLOCKED", "risk_score": 94.5})
    store.append_audit_event({
        "event_id": "sec_abc123",
        "timestamp": "2026-11-12T10:00:00+00:00",
        "event_type": "FRAUD_TRIAGE",
        "actor_email": "admin@nexusretail.ai",
        "actor_role": "admin",
        "tenant_id": "tenant_uk_flagship",
        "action": "Blocked anomalous transfer",
        "status_code": 200,
        "severity": "WARNING",
    })
    store.save_tenant({
        "tenant_id": "tenant_ap_tokyo",
        "name": "Nexus Japan GK",
        "country": "Japan",
        "currency": "JPY",
        "plan": "Enterprise",
        "status": "ACTIVE",
        "created_at": "2026-11-12T10:00:00+00:00",
    })
    store.save_campaign({"campaign_id": "CMP-01", "voucher_code": "VIP-20-AB12", "timestamp": "2026-11-12T10:05:00+00:00"})
    store.save_channel_config("slack", {"webhook_url": "https://hooks.slack.com/services/T/B/X", "enabled": True, "status": "LIVE_CONNECTED", "deliveries": 3})

    reloaded = SQLiteStateStore(db_path=db_file)
    diag = reloaded.checkpoint()

    assert diag["status"] == "persistent"
    assert diag["journal_mode"] == "WAL"
    assert diag["tables"]["fraud_alerts"] == 1
    assert diag["tables"]["audit_events"] == 1
    assert diag["tables"]["tenants"] == 1
    assert diag["tables"]["campaigns"] == 1
    assert diag["tables"]["channel_configs"] == 1


def test_api_persistence_diagnostics_and_wal_checkpoint():
    """Verify FastAPI persistence-status and WAL checkpoint endpoints return live diagnostics."""
    status_res = client.get("/api/v1/system/persistence-status")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["status"] == "persistent"
    assert data["engine"] == "SQLite3"
    assert "audit_events" in data["tables"]

    chk_res = client.post("/api/v1/system/persistence/checkpoint")
    assert chk_res.status_code == 200
    chk_data = chk_res.json()
    assert chk_data["status"] == "checkpointed"
    assert chk_data["total_persisted_records"] >= 1
