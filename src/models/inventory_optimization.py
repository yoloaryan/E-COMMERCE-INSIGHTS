"""
AI Inventory & Supply Chain Optimization Engine (Phase 17).

Combines operations research & empirical UCI demand telemetry to provide:
1. ABC-XYZ Pareto + Demand Volatility Segmentation across retail SKUs.
2. Service-level calibrated Safety Stock (Z * sigma_d * sqrt(lead_time))
   and Dynamic Reorder Point (ROP = mu_d * lead_time + SS).
3. Wilson Economic Order Quantity (EOQ = sqrt(2 * D * S / H)) cost minimization
   vs naive monthly fixed ordering policies.
4. 30-day Inventory Depletion & Sawtooth Replenishment simulation and
   stateful Purchase Order execution ledger.
"""

import math
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.utils.state_store import SQLiteStateStore, get_state_store

DATA_PROCESSED_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"

Z_TABLE = {
    0.85: 1.0364,
    0.90: 1.2816,
    0.92: 1.4051,
    0.95: 1.6449,
    0.98: 2.0537,
    0.99: 2.3263,
}

# Seed catalog synchronized with core flagship SKUs + deadstock examples
FLAGSHIP_SKUS: List[Dict[str, Any]] = [
    {"stock_code": "22423", "description": "Regency Cakestand 3 Tier", "unit_price": 10.95, "daily_demand_mean": 38.0, "daily_demand_std": 14.2, "stock_on_hand": 420},
    {"stock_code": "85123A", "description": "White Hanging Heart T-Light Holder", "unit_price": 2.55, "daily_demand_mean": 104.0, "daily_demand_std": 36.5, "stock_on_hand": 1250},
    {"stock_code": "47566", "description": "Party Bunting", "unit_price": 4.65, "daily_demand_mean": 50.0, "daily_demand_std": 19.8, "stock_on_hand": 950},
    {"stock_code": "85099B", "description": "Jumbo Bag Red Retrospot", "unit_price": 1.79, "daily_demand_mean": 132.0, "daily_demand_std": 41.0, "stock_on_hand": 3200},
    {"stock_code": "20725", "description": "Lunch Bag Red Retrospot", "unit_price": 1.65, "daily_demand_mean": 85.0, "daily_demand_std": 27.4, "stock_on_hand": 2400},
    {"stock_code": "22699", "description": "Roses Regency Teacup And Saucer", "unit_price": 2.95, "daily_demand_mean": 29.0, "daily_demand_std": 12.6, "stock_on_hand": 210},
    {"stock_code": "22697", "description": "Green Regency Teacup And Saucer", "unit_price": 2.95, "daily_demand_mean": 27.0, "daily_demand_std": 11.4, "stock_on_hand": 180},
    {"stock_code": "22086", "description": "Paper Chain Kit 50's Christmas", "unit_price": 2.55, "daily_demand_mean": 64.0, "daily_demand_std": 58.2, "stock_on_hand": 880},
    {"stock_code": "84879", "description": "Assorted Colour Bird Ornament", "unit_price": 1.69, "daily_demand_mean": 96.0, "daily_demand_std": 31.8, "stock_on_hand": 1900},
    {"stock_code": "22197", "description": "Popcorn Holder", "unit_price": 0.85, "daily_demand_mean": 115.0, "daily_demand_std": 42.0, "stock_on_hand": 3600},
    {"stock_code": "21212", "description": "Pack Of 72 Retrospot Cake Cases", "unit_price": 0.55, "daily_demand_mean": 78.0, "daily_demand_std": 28.5, "stock_on_hand": 9500},
    {"stock_code": "22720", "description": "Set Of 3 Cake Tins Pantry Design", "unit_price": 4.95, "daily_demand_mean": 3.4, "daily_demand_std": 3.9, "stock_on_hand": 1420},
]


def _service_level_to_z(service_level: float) -> float:
    """Maps a target cycle service level in (0.5, 0.999) to a standard normal Z-score."""
    sl = max(0.51, min(0.999, float(service_level)))
    # Check exact lookup table first
    for k, v in Z_TABLE.items():
        if abs(sl - k) < 1e-4:
            return v
    # Piecewise linear interpolation between sorted anchor points
    anchors = sorted([(0.50, 0.0), (0.85, 1.0364), (0.90, 1.2816), (0.92, 1.4051),
                      (0.95, 1.6449), (0.98, 2.0537), (0.99, 2.3263), (0.999, 3.0902)])
    for (x0, y0), (x1, y1) in zip(anchors[:-1], anchors[1:]):
        if x0 <= sl <= x1:
            t = (sl - x0) / (x1 - x0)
            return round(y0 + t * (y1 - y0), 4)
    return 1.6449


def _normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


class InventoryOptimizationEngine:
    """Stateful Inventory & Supply Chain Optimization Engine."""

    def __init__(self, use_parquet: bool = True, state_store: Optional[SQLiteStateStore] = None):
        self.skus: Dict[str, Dict[str, Any]] = {}
        self.purchase_orders: List[Dict[str, Any]] = []
        self.data_source: str = "synthetic_fallback"
        self.state_store: SQLiteStateStore = state_store or get_state_store()
        self._load_catalog(use_parquet=use_parquet)
        self._hydrate_persisted_state()
        self._assign_abc_xyz()

    def _hydrate_persisted_state(self) -> None:
        """Restores custom/updated SKUs and Purchase Orders from SQLite persistence."""
        try:
            for row in self.state_store.load_custom_skus():
                code = str(row["stock_code"]).upper()
                self.skus[code] = {
                    "stock_code": code,
                    "description": row["description"],
                    "unit_price": float(row["unit_price"]),
                    "daily_demand_mean": float(row["daily_demand_mean"]),
                    "daily_demand_std": float(row["daily_demand_std"]),
                    "stock_on_hand": int(row["stock_on_hand"]),
                    "in_transit": int(row.get("in_transit", 0)),
                }
            pos = self.state_store.load_purchase_orders()
            if pos:
                self.purchase_orders = pos
        except Exception:
            pass

    def _load_catalog(self, use_parquet: bool = True) -> None:
        # Seed baseline flagship SKUs first so known codes always retain realistic stock positions
        flagship_map = {item["stock_code"]: dict(item) for item in FLAGSHIP_SKUS}

        if use_parquet and DATA_PROCESSED_PATH.exists():
            try:
                df = pd.read_parquet(
                    DATA_PROCESSED_PATH,
                    columns=["StockCode", "Description", "Quantity", "UnitPrice", "InvoiceDate"],
                )
                df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)].copy()
                df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
                df["Date"] = pd.to_datetime(df["InvoiceDate"]).dt.date
                span_days = max(1, (df["Date"].max() - df["Date"].min()).days + 1)

                daily = df.groupby(["StockCode", "Date"])["Quantity"].sum().reset_index()
                stats = daily.groupby("StockCode").agg(
                    total_qty=("Quantity", "sum"),
                    active_days=("Quantity", "count"),
                    active_std=("Quantity", "std"),
                ).reset_index()
                meta = df.groupby("StockCode").agg(
                    description=("Description", "first"),
                    unit_price=("UnitPrice", "median"),
                ).reset_index()
                merged = stats.merge(meta, on="StockCode", how="left")
                merged["mu_d"] = (merged["total_qty"] / float(span_days)).clip(lower=0.5)
                merged["sigma_d"] = merged["active_std"].fillna(merged["mu_d"] * 0.45).clip(lower=0.2)

                # Keep top 18 SKUs by volume + all flagship SKUs
                top_rows = merged.sort_values("total_qty", ascending=False).head(18)
                top_codes = set(top_rows["StockCode"].tolist()) | set(flagship_map.keys())
                subset = merged[merged["StockCode"].isin(top_codes)]

                for _, row in subset.iterrows():
                    code = str(row["StockCode"])
                    mu_d = round(float(row["mu_d"]), 2)
                    sigma_d = round(float(row["sigma_d"]), 2)
                    price = round(float(row["unit_price"]), 2)
                    if code in flagship_map:
                        base = flagship_map[code]
                        # Preserve tuned flagship burn/stock levels when close; calibrate variance from parquet
                        self.skus[code] = {
                            "stock_code": code,
                            "description": base["description"],
                            "unit_price": base["unit_price"],
                            "daily_demand_mean": base["daily_demand_mean"],
                            "daily_demand_std": round(max(base["daily_demand_std"], min(sigma_d, base["daily_demand_mean"] * 1.4)), 2),
                            "stock_on_hand": int(base["stock_on_hand"]),
                            "in_transit": 0,
                        }
                    else:
                        # Deterministic stock position derived from hash so CI & restarts match identically
                        days_cover = 10 + (sum(ord(c) for c in code) % 28)
                        self.skus[code] = {
                            "stock_code": code,
                            "description": str(row["description"] or f"Retail SKU {code}").strip()[:55].title(),
                            "unit_price": max(0.25, price),
                            "daily_demand_mean": mu_d,
                            "daily_demand_std": sigma_d,
                            "stock_on_hand": int(max(25, round(mu_d * days_cover))),
                            "in_transit": 0,
                        }
                self.data_source = "parquet_historical"
                return
            except Exception:
                pass

        for code, item in flagship_map.items():
            self.skus[code] = {**item, "in_transit": 0}
        self.data_source = "synthetic_fallback"

    def _assign_abc_xyz(self) -> None:
        """Assigns ABC revenue tiers and XYZ volatility tiers across all SKUs."""
        revs = []
        for code, sku in self.skus.items():
            annual_rev = float(sku["daily_demand_mean"]) * 365.0 * float(sku["unit_price"])
            revs.append((code, annual_rev))
        revs.sort(key=lambda x: x[1], reverse=True)
        total_rev = max(1.0, sum(r for _, r in revs))

        cum = 0.0
        for code, rev in revs:
            cum += rev
            share = cum / total_rev
            abc = "A" if share <= 0.72 else ("B" if share <= 0.92 else "C")
            mu = max(0.05, float(self.skus[code]["daily_demand_mean"]))
            cv = float(self.skus[code]["daily_demand_std"]) / mu
            xyz = "X" if cv < 0.45 else ("Y" if cv < 0.85 else "Z")
            self.skus[code]["abc_class"] = abc
            self.skus[code]["xyz_class"] = xyz
            self.skus[code]["abc_xyz"] = f"{abc}{xyz}"
            self.skus[code]["annual_revenue_est"] = round(rev, 2)

    def compute_sku_policy(
        self,
        sku: Dict[str, Any],
        service_level: float = 0.95,
        lead_time_days: int = 7,
        ordering_cost: float = 45.0,
        holding_rate: float = 0.22,
        demand_multiplier: float = 1.0,
        stock_override: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Computes Safety Stock, Reorder Point, Wilson EOQ, Risk & Cost Breakdown for one SKU."""
        z = _service_level_to_z(service_level)
        lt = max(1, min(60, int(lead_time_days)))
        mult = max(0.25, min(4.0, float(demand_multiplier)))
        ord_cost = max(5.0, float(ordering_cost))
        h_rate = max(0.05, min(0.80, float(holding_rate)))

        mu_d = round(float(sku["daily_demand_mean"]) * mult, 2)
        sigma_d = round(float(sku["daily_demand_std"]) * math.sqrt(mult), 2)
        annual_demand = max(1.0, mu_d * 365.0)

        unit_price = float(sku["unit_price"])
        unit_cost = max(0.25, round(unit_price * 0.62, 2))
        annual_unit_holding = max(0.05, unit_cost * h_rate)

        safety_stock = max(1, int(round(z * sigma_d * math.sqrt(lt))))
        reorder_point = max(safety_stock + 1, int(round(mu_d * lt + safety_stock)))
        eoq = max(10, int(round(math.sqrt((2.0 * annual_demand * ord_cost) / annual_unit_holding))))

        stock_on_hand = int(stock_override) if stock_override is not None else int(sku["stock_on_hand"])
        in_transit = int(sku.get("in_transit", 0))
        effective_stock = stock_on_hand + in_transit

        days_remaining = round(stock_on_hand / max(0.05, mu_d), 1)
        lt_demand_mean = mu_d * lt
        lt_demand_std = max(0.1, sigma_d * math.sqrt(lt))
        z_current = (lt_demand_mean - effective_stock) / lt_demand_std
        stockout_prob_pct = round(max(0.1, min(99.9, _normal_cdf(z_current) * 100.0)), 1)

        # Economic Order Quantity Cost vs Naive Fixed Monthly Ordering (12 cycles/year)
        orders_per_year = annual_demand / float(eoq)
        annual_ordering_cost = round(orders_per_year * ord_cost, 2)
        annual_holding_cost = round(((eoq / 2.0) + safety_stock) * annual_unit_holding, 2)
        annual_total_cost = round(annual_ordering_cost + annual_holding_cost, 2)

        naive_qty = max(1.0, annual_demand / 12.0)
        naive_total_cost = round((12.0 * ord_cost) + (((naive_qty / 2.0) + safety_stock) * annual_unit_holding), 2)
        annual_eoq_savings = round(max(0.0, naive_total_cost - annual_total_cost), 2)

        inventory_value = round(stock_on_hand * unit_cost, 2)
        is_overstock = days_remaining > 75.0 or stock_on_hand > (reorder_point + eoq * 2.0)

        if effective_stock <= reorder_point * 0.85 or days_remaining <= lt + 3:
            risk_status = "CRITICAL_REORDER"
            action_label = f"Issue PO (+{eoq} units)"
        elif effective_stock <= reorder_point * 1.2 or days_remaining <= lt + 8:
            risk_status = "REORDER_SOON"
            action_label = f"Queue PO (+{eoq} units)"
        elif is_overstock:
            risk_status = "OVERSTOCK_MARKDOWN"
            action_label = "Bundle / 15% Markdown"
        else:
            risk_status = "OPTIMAL"
            action_label = "Healthy Buffer"

        return {
            "stock_code": sku["stock_code"],
            "description": sku["description"],
            "unit_price": round(unit_price, 2),
            "unit_cost": unit_cost,
            "abc_class": sku.get("abc_class", "B"),
            "xyz_class": sku.get("xyz_class", "Y"),
            "abc_xyz": sku.get("abc_xyz", "BY"),
            "stock_on_hand": stock_on_hand,
            "in_transit": in_transit,
            "effective_stock": effective_stock,
            "daily_demand_mean": mu_d,
            "daily_demand_std": sigma_d,
            "annual_demand": round(annual_demand, 0),
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "eoq": eoq,
            "days_remaining": days_remaining,
            "stockout_probability_pct": stockout_prob_pct,
            "annual_ordering_cost": annual_ordering_cost,
            "annual_holding_cost": annual_holding_cost,
            "annual_total_cost": annual_total_cost,
            "annual_eoq_savings": annual_eoq_savings,
            "inventory_value_gbp": inventory_value,
            "overstock_capital_gbp": inventory_value if is_overstock else 0.0,
            "risk_status": risk_status,
            "action_label": action_label,
        }

    def simulate_sku(
        self,
        stock_code: str,
        service_level: float = 0.95,
        lead_time_days: int = 7,
        ordering_cost: float = 45.0,
        holding_rate: float = 0.22,
        demand_multiplier: float = 1.0,
        stock_override: Optional[int] = None,
        horizon_days: int = 30,
    ) -> Dict[str, Any]:
        """Simulates SKU policy plus a 30-day depletion & EOQ sawtooth replenishment curve."""
        code = str(stock_code).strip().upper()
        if code not in self.skus:
            raise KeyError(f"SKU '{code}' not found in optimization catalog.")

        policy = self.compute_sku_policy(
            self.skus[code],
            service_level=service_level,
            lead_time_days=lead_time_days,
            ordering_cost=ordering_cost,
            holding_rate=holding_rate,
            demand_multiplier=demand_multiplier,
            stock_override=stock_override,
        )

        mu = policy["daily_demand_mean"]
        rop = policy["reorder_point"]
        eoq = policy["eoq"]
        lt = max(1, min(60, int(lead_time_days)))
        horizon = max(7, min(60, int(horizon_days)))

        baseline_cur = float(policy["stock_on_hand"])
        optimized_cur = float(policy["stock_on_hand"])
        pending_arrival_day: Optional[int] = None

        trajectory: List[Dict[str, Any]] = []
        for day in range(0, horizon + 1):
            if day > 0:
                baseline_cur = max(0.0, baseline_cur - mu)
                optimized_cur = max(0.0, optimized_cur - mu)

                if pending_arrival_day is not None and day == pending_arrival_day:
                    optimized_cur += float(eoq)
                    pending_arrival_day = None

                if optimized_cur <= rop and pending_arrival_day is None:
                    pending_arrival_day = day + lt

            trajectory.append({
                "day": day,
                "label": f"Day {day}",
                "unmanaged_stock": round(baseline_cur, 1),
                "eoq_managed_stock": round(optimized_cur, 1),
                "safety_stock": policy["safety_stock"],
                "reorder_point": rop,
            })

        return {
            "policy": policy,
            "parameters": {
                "service_level": round(float(service_level), 3),
                "z_score": _service_level_to_z(service_level),
                "lead_time_days": lt,
                "ordering_cost": round(float(ordering_cost), 2),
                "holding_rate": round(float(holding_rate), 3),
                "demand_multiplier": round(float(demand_multiplier), 2),
            },
            "trajectory": trajectory,
        }

    def generate_optimization_report(
        self,
        service_level: float = 0.95,
        lead_time_days: int = 7,
        ordering_cost: float = 45.0,
        holding_rate: float = 0.22,
    ) -> Dict[str, Any]:
        """Generates full catalog optimization ledger, KPIs, and ABC-XYZ summary."""
        rows = [
            self.compute_sku_policy(
                sku,
                service_level=service_level,
                lead_time_days=lead_time_days,
                ordering_cost=ordering_cost,
                holding_rate=holding_rate,
            )
            for sku in self.skus.values()
        ]
        # Order critical stockouts first, then overstock/other
        status_rank = {
            "CRITICAL_REORDER": 0,
            "REORDER_SOON": 1,
            "OVERSTOCK_MARKDOWN": 2,
            "OPTIMAL": 3,
        }
        rows.sort(key=lambda r: (status_rank.get(r["risk_status"], 9), r["days_remaining"]))

        critical_count = sum(1 for r in rows if r["risk_status"] == "CRITICAL_REORDER")
        reorder_soon_count = sum(1 for r in rows if r["risk_status"] == "REORDER_SOON")
        overstock_count = sum(1 for r in rows if r["risk_status"] == "OVERSTOCK_MARKDOWN")
        total_inventory_value = round(sum(r["inventory_value_gbp"] for r in rows), 2)
        overstock_capital = round(sum(r["overstock_capital_gbp"] for r in rows), 2)
        annual_eoq_savings = round(sum(r["annual_eoq_savings"] for r in rows), 2)

        abc_counts = {"A": 0, "B": 0, "C": 0}
        for r in rows:
            abc_counts[r["abc_class"]] = abc_counts.get(r["abc_class"], 0) + 1

        return {
            "status": "healthy",
            "data_source": self.data_source,
            "parameters": {
                "service_level": round(float(service_level), 3),
                "z_score": _service_level_to_z(service_level),
                "lead_time_days": int(lead_time_days),
                "ordering_cost": float(ordering_cost),
                "holding_rate": float(holding_rate),
            },
            "kpis": {
                "active_skus_monitored": len(rows),
                "critical_reorder_skus": critical_count,
                "reorder_soon_skus": reorder_soon_count,
                "overstock_skus": overstock_count,
                "total_inventory_value_gbp": total_inventory_value,
                "overstock_capital_gbp": overstock_capital,
                "annual_eoq_savings_gbp": annual_eoq_savings,
                "abc_distribution": abc_counts,
            },
            "skus": rows,
            "purchase_orders": list(reversed(self.purchase_orders[-25:])),
        }

    def issue_purchase_order(
        self,
        stock_code: str,
        order_qty: Optional[int] = None,
        lead_time_days: int = 7,
        service_level: float = 0.95,
        ordering_cost: float = 45.0,
        holding_rate: float = 0.22,
        actor_email: str = "supply@nexusretail.ai",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Issues an audited Purchase Order, replenishing stock on hand immediately for simulation visibility."""
        code = str(stock_code).strip().upper()
        if code not in self.skus:
            raise KeyError(f"SKU '{code}' not found in catalog.")

        policy_before = self.compute_sku_policy(
            self.skus[code],
            service_level=service_level,
            lead_time_days=lead_time_days,
            ordering_cost=ordering_cost,
            holding_rate=holding_rate,
        )
        qty = int(order_qty) if order_qty is not None and int(order_qty) > 0 else int(policy_before["eoq"])
        qty = max(1, min(100000, qty))

        self.skus[code]["stock_on_hand"] = int(self.skus[code]["stock_on_hand"]) + qty
        policy_after = self.compute_sku_policy(
            self.skus[code],
            service_level=service_level,
            lead_time_days=lead_time_days,
            ordering_cost=ordering_cost,
            holding_rate=holding_rate,
        )

        po_cost = round(qty * policy_after["unit_cost"], 2)
        po = {
            "po_id": f"PO-{secrets.token_hex(3).upper()}",
            "stock_code": code,
            "description": self.skus[code]["description"],
            "order_qty": qty,
            "unit_cost_gbp": policy_after["unit_cost"],
            "total_cost_gbp": po_cost,
            "lead_time_days": int(lead_time_days),
            "new_stock_on_hand": policy_after["stock_on_hand"],
            "new_days_remaining": policy_after["days_remaining"],
            "status": "DISPATCHED",
            "issued_by": actor_email,
            "notes": notes.strip()[:200] if notes else "EOQ Automated Replenishment",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.purchase_orders.append(po)
        self.state_store.save_purchase_order(po)
        self.state_store.upsert_sku(self.skus[code])
        return {"purchase_order": po, "updated_policy": policy_after}

    def add_sku(
        self,
        stock_code: str,
        description: str,
        unit_price: float,
        daily_demand_mean: float,
        daily_demand_std: Optional[float] = None,
        stock_on_hand: int = 100,
    ) -> Dict[str, Any]:
        """Adds or updates a catalog SKU in the live optimization engine."""
        code = str(stock_code).strip().upper()
        if not code:
            raise ValueError("stock_code must not be empty.")
        mu = max(0.5, float(daily_demand_mean))
        sigma = float(daily_demand_std) if daily_demand_std is not None else round(mu * 0.35, 2)
        self.skus[code] = {
            "stock_code": code,
            "description": str(description).strip()[:64] or f"Custom SKU {code}",
            "unit_price": max(0.25, float(unit_price)),
            "daily_demand_mean": round(mu, 2),
            "daily_demand_std": round(max(0.1, sigma), 2),
            "stock_on_hand": max(0, int(stock_on_hand)),
            "in_transit": 0,
        }
        self._assign_abc_xyz()
        self.state_store.upsert_sku(self.skus[code])
        return self.compute_sku_policy(self.skus[code])


_INVENTORY_ENGINE_SINGLETON: Optional[InventoryOptimizationEngine] = None


def get_inventory_engine() -> InventoryOptimizationEngine:
    """Returns process-wide singleton InventoryOptimizationEngine instance."""
    global _INVENTORY_ENGINE_SINGLETON
    if _INVENTORY_ENGINE_SINGLETON is None:
        _INVENTORY_ENGINE_SINGLETON = InventoryOptimizationEngine()
    return _INVENTORY_ENGINE_SINGLETON

