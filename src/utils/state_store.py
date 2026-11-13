"""
Persistent SQLite State Store & Operational Telemetry Repository (Phase 19).

Provides lightweight, zero-dependency ACID SQLite (WAL mode) persistence across
operational registries so state survives FastAPI / uvicorn restarts and Docker redeploys:
1. purchase_orders: Inventory EOQ Purchase Orders Ledger.
2. custom_skus: Catalog SKU additions & updated stock-on-hand levels.
3. fraud_alerts: Quarantined transactions & operator triage decisions.
4. audit_events: Enterprise security & RBAC governance event stream.
5. tenants: Provisioned multi-tenant organization workspaces.
6. campaigns: Dispatched retention campaigns ledger.
7. channel_configs: Slack / Discord / Email channel connection states.
"""

import json
import os
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DB = (
    ROOT_DIR / "data" / "state" / "prism_state.db"
    if (ROOT_DIR / "data" / "state" / "prism_state.db").exists() or not (ROOT_DIR / "data" / "state" / "nexus_state.db").exists()
    else ROOT_DIR / "data" / "state" / "nexus_state.db"
)


def resolve_default_db_path() -> Path:
    """Resolves production DB path vs isolated process-scoped test DB under pytest."""
    env_override = os.environ.get("PRISM_STATE_DB") or os.environ.get("NEXUS_STATE_DB")
    if env_override:
        return Path(env_override)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / f"prism_pytest_state_{os.getpid()}.db"
    return DEFAULT_STATE_DB


class SQLiteStateStore:
    """Thread-safe SQLite (WAL) state store backing Prism Retail operational registries."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path is not None else resolve_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    po_id TEXT PRIMARY KEY,
                    stock_code TEXT NOT NULL,
                    description TEXT,
                    order_qty INTEGER NOT NULL,
                    unit_cost_gbp REAL NOT NULL,
                    total_cost_gbp REAL NOT NULL,
                    lead_time_days INTEGER NOT NULL,
                    new_stock_on_hand INTEGER NOT NULL,
                    new_days_remaining REAL NOT NULL,
                    status TEXT NOT NULL,
                    issued_by TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_skus (
                    stock_code TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    unit_price REAL NOT NULL,
                    daily_demand_mean REAL NOT NULL,
                    daily_demand_std REAL NOT NULL,
                    stock_on_hand INTEGER NOT NULL,
                    in_transit INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS fraud_alerts (
                    alert_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_email TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    severity TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    country TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_configs (
                    channel TEXT PRIMARY KEY,
                    webhook_url TEXT,
                    enabled INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    deliveries INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()

    # -- Inventory POs & SKUs --------------------------------------------------
    def save_purchase_order(self, po: Dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO purchase_orders (
                    po_id, stock_code, description, order_qty, unit_cost_gbp,
                    total_cost_gbp, lead_time_days, new_stock_on_hand, new_days_remaining,
                    status, issued_by, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                po["po_id"], po["stock_code"], po.get("description", ""),
                int(po["order_qty"]), float(po["unit_cost_gbp"]), float(po["total_cost_gbp"]),
                int(po["lead_time_days"]), int(po["new_stock_on_hand"]), float(po["new_days_remaining"]),
                po["status"], po["issued_by"], po.get("notes", ""), po["created_at"],
            ))
            conn.commit()

    def load_purchase_orders(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM purchase_orders ORDER BY created_at ASC LIMIT ?", (int(limit),)
            ).fetchall()
            return [dict(r) for r in rows]

    def upsert_sku(self, sku: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO custom_skus (
                    stock_code, description, unit_price, daily_demand_mean,
                    daily_demand_std, stock_on_hand, in_transit, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sku["stock_code"], sku["description"], float(sku["unit_price"]),
                float(sku["daily_demand_mean"]), float(sku["daily_demand_std"]),
                int(sku["stock_on_hand"]), int(sku.get("in_transit", 0)), now,
            ))
            conn.commit()

    def load_custom_skus(self) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM custom_skus").fetchall()
            return [dict(r) for r in rows]

    # -- Fraud Quarantine Alerts ----------------------------------------------
    def save_fraud_alert(self, alert: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO fraud_alerts (alert_id, payload_json, updated_at)
                VALUES (?, ?, ?)
            """, (alert["alert_id"], json.dumps(alert), now))
            conn.commit()

    def load_fraud_alerts(self) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM fraud_alerts ORDER BY updated_at DESC"
            ).fetchall()
            return [json.loads(r["payload_json"]) for r in rows]

    # -- Security Audit Stream & Tenants --------------------------------------
    def append_audit_event(self, entry: Dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                INSERT INTO audit_events (
                    event_id, timestamp, event_type, actor_email, actor_role,
                    tenant_id, action, status_code, severity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry["event_id"], entry["timestamp"], entry["event_type"],
                entry["actor_email"], entry["actor_role"], entry["tenant_id"],
                entry["action"], int(entry["status_code"]), entry["severity"],
            ))
            conn.commit()

    def load_audit_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("""
                SELECT event_id, timestamp, event_type, actor_email, actor_role,
                       tenant_id, action, status_code, severity
                FROM audit_events
                ORDER BY seq DESC
                LIMIT ?
            """, (int(limit),)).fetchall()
            return [dict(r) for r in rows]

    def save_tenant(self, tenant: Dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tenants (
                    tenant_id, name, country, currency, plan, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                tenant["tenant_id"], tenant["name"], tenant["country"],
                tenant["currency"], tenant["plan"], tenant["status"], tenant["created_at"],
            ))
            conn.commit()

    def load_tenants(self) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM tenants").fetchall()
            return [dict(r) for r in rows]

    # -- Campaigns & Channel Webhooks -----------------------------------------
    def save_campaign(self, campaign: Dict[str, Any]) -> None:
        cid = str(campaign.get("campaign_id") or campaign.get("voucher_code") or f"CMP-{hash(json.dumps(campaign, sort_keys=True))}")
        created = str(campaign.get("timestamp") or datetime.now(timezone.utc).isoformat())
        with self._lock, self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO campaigns (campaign_id, payload_json, created_at)
                VALUES (?, ?, ?)
            """, (cid, json.dumps(campaign), created))
            conn.commit()

    def load_campaigns(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM campaigns ORDER BY created_at DESC LIMIT ?", (int(limit),)
            ).fetchall()
            return [json.loads(r["payload_json"]) for r in rows]

    def save_channel_config(self, channel: str, cfg: Dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO channel_configs (
                    channel, webhook_url, enabled, status, deliveries
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                channel, cfg.get("webhook_url", ""), 1 if cfg.get("enabled", True) else 0,
                cfg.get("status", "SIMULATED_DEV"), int(cfg.get("deliveries", 0)),
            ))
            conn.commit()

    def load_channel_configs(self) -> List[Dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM channel_configs").fetchall()
            return [dict(r) for r in rows]

    # -- Maintenance & Telemetry Diagnostics ----------------------------------
    def checkpoint(self) -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.commit()
        return self.get_storage_diagnostics()

    def get_storage_diagnostics(self) -> Dict[str, Any]:
        table_names = [
            "purchase_orders", "custom_skus", "fraud_alerts",
            "audit_events", "tenants", "campaigns", "channel_configs",
        ]
        counts: Dict[str, int] = {}
        with self._lock, self._connect() as conn:
            mode_row = conn.execute("PRAGMA journal_mode;").fetchone()
            journal_mode = str(mode_row[0]).upper() if mode_row else "UNKNOWN"
            for tbl in table_names:
                c = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                counts[tbl] = int(c)

        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "status": "persistent",
            "engine": "SQLite3",
            "journal_mode": journal_mode,
            "db_path": str(self.db_path),
            "size_kb": round(size_bytes / 1024.0, 2),
            "total_persisted_records": sum(counts.values()),
            "tables": counts,
        }


_STATE_STORE_SINGLETON: Optional[SQLiteStateStore] = None
_STATE_STORE_PATH_KEY: Optional[str] = None


def get_state_store(db_path: Optional[Path] = None) -> SQLiteStateStore:
    """Returns process-wide singleton SQLiteStateStore matching the active DB target."""
    global _STATE_STORE_SINGLETON, _STATE_STORE_PATH_KEY
    resolved = str(Path(db_path) if db_path is not None else resolve_default_db_path())
    if _STATE_STORE_SINGLETON is None or _STATE_STORE_PATH_KEY != resolved:
        _STATE_STORE_SINGLETON = SQLiteStateStore(db_path=Path(resolved))
        _STATE_STORE_PATH_KEY = resolved
    return _STATE_STORE_SINGLETON
