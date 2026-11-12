"""
Transaction Anomaly, Fraud & Cancellation Intelligence Engine.

Combines:
1. Unsupervised Isolation Forest trained on invoice-level behavioral vectors
   (log_abs_amount, log1p_units, line_items, avg_unit_price, off_hours_flag, is_guest).
2. Historical account cancellation propensity scoring & country cancellation analytics.
3. Robust Z-score outlier triggers (order amount spikes, quantity bursts, off-hour guest checkouts).
4. Stateful AnomalyRegistry singleton for live transaction quarantine & operator triage.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.utils.state_store import get_state_store

from datetime import datetime, timezone
import math
import secrets
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


DATA_PROCESSED_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"

FEATURE_COLS = [
    "log_abs_amount",
    "log1p_units",
    "line_items",
    "log1p_avg_price",
    "is_off_hours",
    "is_guest",
]


def _build_synthetic_invoice_corpus(seed: int = 42) -> pd.DataFrame:
    """
    Deterministic fallback invoice corpus used when processed Parquet is absent (e.g. CI checkouts).
    """
    rng = np.random.default_rng(seed)
    n_normal = 900
    countries = ["United Kingdom", "Germany", "France", "EIRE", "Netherlands", "Spain"]

    normal_rev = rng.lognormal(mean=5.4, sigma=0.85, size=n_normal)
    normal_qty = np.maximum(1, np.round(normal_rev / rng.uniform(2.0, 5.0, size=n_normal))).astype(int)
    normal_lines = np.maximum(1, rng.poisson(lam=14, size=n_normal))
    normal_hours = rng.integers(8, 19, size=n_normal)
    normal_guest = rng.choice([False, True], size=n_normal, p=[0.85, 0.15])
    normal_cancel = rng.choice([False, True], size=n_normal, p=[0.90, 0.10])
    normal_country = rng.choice(countries, size=n_normal, p=[0.80, 0.06, 0.05, 0.04, 0.03, 0.02])

    rows: List[Dict[str, Any]] = []
    for i in range(n_normal):
        is_c = bool(normal_cancel[i])
        rev = round(-normal_rev[i] if is_c else normal_rev[i], 2)
        qty = int(-normal_qty[i] if is_c else normal_qty[i])
        rows.append({
            "InvoiceNo": f"{'C' if is_c else ''}SIM{540000 + i}",
            "CustomerID": "None" if normal_guest[i] else str(12500 + (i % 120)),
            "Country": str(normal_country[i]),
            "rev": rev,
            "qty": qty,
            "lines": int(normal_lines[i]),
            "is_cancel": is_c,
            "is_guest": bool(normal_guest[i]),
            "hour": float(normal_hours[i]),
        })

    # Inject realistic anomalies matching historical extreme spikes & cancellations
    outliers = [
        {"InvoiceNo": "581483", "CustomerID": "16446", "Country": "United Kingdom", "rev": 168469.60, "qty": 80995, "lines": 1, "is_cancel": False, "is_guest": False, "hour": 9.0},
        {"InvoiceNo": "C581484", "CustomerID": "16446", "Country": "United Kingdom", "rev": -168469.60, "qty": -80995, "lines": 1, "is_cancel": True, "is_guest": False, "hour": 9.0},
        {"InvoiceNo": "574941", "CustomerID": "None", "Country": "United Kingdom", "rev": 52940.94, "qty": 14149, "lines": 101, "is_cancel": False, "is_guest": True, "hour": 2.0},
        {"InvoiceNo": "C556445", "CustomerID": "15098", "Country": "United Kingdom", "rev": -38970.00, "qty": -60, "lines": 1, "is_cancel": True, "is_guest": False, "hour": 15.0},
    ]
    rows.extend(outliers)
    return pd.DataFrame(rows)


def _featurize_invoices(df_inv: pd.DataFrame) -> pd.DataFrame:
    """Engineers Isolation Forest numerical feature matrix from invoice aggregates."""
    abs_rev = df_inv["rev"].abs().clip(lower=0.01)
    abs_qty = df_inv["qty"].abs().clip(lower=1.0)
    avg_p = (abs_rev / abs_qty).clip(lower=0.05)
    hours = df_inv["hour"].fillna(12.0).astype(float)

    feats = pd.DataFrame({
        "log_abs_amount": np.log1p(abs_rev),
        "log1p_units": np.log1p(abs_qty),
        "line_items": df_inv["lines"].clip(lower=1).astype(float),
        "log1p_avg_price": np.log1p(avg_p),
        "is_off_hours": ((hours < 6.0) | (hours >= 22.0)).astype(float),
        "is_guest": df_inv["is_guest"].astype(float),
    }, index=df_inv.index)
    return feats


class AnomalyRegistry:
    """Singleton ledger holding quarantined transactions and fraud alert events."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AnomalyRegistry, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.quarantine_queue: List[Dict[str, Any]] = [
            {
                "alert_id": "FRD-581483",
                "invoice_no": "581483",
                "customer_id": "16446",
                "country": "United Kingdom",
                "amount_gbp": 168469.60,
                "total_units": 80995,
                "risk_score": 96.4,
                "risk_tier": "CRITICAL_QUARANTINE",
                "recommended_action": "QUARANTINE_AND_HOLD",
                "triggered_signals": [
                    "Order value ₹1,68,469.60 exceeds 99.9th catalog percentile",
                    "Single-SKU bulk quantity anomaly (80,995 units on 1 line)",
                ],
                "status": "QUARANTINED",
                "timestamp": "2026-11-11T09:15:00+00:00",
            },
            {
                "alert_id": "FRD-574941",
                "invoice_no": "574941",
                "customer_id": "Guest Checkout",
                "country": "United Kingdom",
                "amount_gbp": 52940.94,
                "total_units": 14149,
                "risk_score": 89.2,
                "risk_tier": "CRITICAL_QUARANTINE",
                "recommended_action": "QUARANTINE_AND_HOLD",
                "triggered_signals": [
                    "Unauthenticated guest checkout exceeding ₹2,000 threshold",
                    "101-line basket structural spike (+8.9σ)",
                ],
                "status": "QUARANTINED",
                "timestamp": "2026-11-11T17:42:00+00:00",
            },
        ]
        try:
            persisted = get_state_store().load_fraud_alerts()
            if persisted:
                by_id = {item["alert_id"]: item for item in self.quarantine_queue}
                for p in persisted:
                    by_id[p["alert_id"]] = p
                # Preserve newest persisted items ahead of unmodified defaults
                seen_ids = {p["alert_id"] for p in persisted}
                merged = list(persisted) + [item for item in self.quarantine_queue if item["alert_id"] not in seen_ids]
                self.quarantine_queue = merged[:40]
        except Exception:
            pass

    def enqueue_alert(self, alert: Dict[str, Any]):
        self.quarantine_queue.insert(0, alert)
        if len(self.quarantine_queue) > 40:
            self.quarantine_queue.pop()
        try:
            get_state_store().save_fraud_alert(alert)
        except Exception:
            pass

    def resolve_alert(self, alert_id: str, decision: str, actor_email: str) -> Optional[Dict[str, Any]]:
        clean_decision = decision.strip().upper()
        if clean_decision not in ("APPROVED", "BLOCKED"):
            raise ValueError("Decision must be 'APPROVED' or 'BLOCKED'.")

        for item in self.quarantine_queue:
            if item["alert_id"] == alert_id:
                item["status"] = clean_decision
                item["resolved_by"] = actor_email
                item["resolved_at"] = datetime.now(timezone.utc).isoformat()
                try:
                    get_state_store().save_fraud_alert(item)
                except Exception:
                    pass
                return item
        return None


class AnomalyDetectionEngine:
    """
    Isolation Forest + Statistical Outlier Scoring Engine for E-Commerce Invoices.
    """

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or DATA_PROCESSED_PATH
        self.data_source: str = "unknown"
        self.df_invoices: pd.DataFrame = pd.DataFrame()
        self.customer_cancel_rates: Dict[str, float] = {}
        self.scaler = StandardScaler()
        self.iso_forest = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42,
        )
        self.baseline_stats: Dict[str, float] = {}
        self._report_cache: Optional[Dict[str, Any]] = None
        self._load_and_fit()

    def _load_and_fit(self):
        if self.data_path.exists():
            raw = pd.read_parquet(
                self.data_path,
                columns=["InvoiceNo", "StockCode", "Quantity", "UnitPrice", "TotalPrice", "CustomerID", "Country", "IsCancelled", "IsGuest", "Hour"],
            )
            inv = raw.groupby("InvoiceNo", as_index=False).agg(
                rev=("TotalPrice", "sum"),
                qty=("Quantity", "sum"),
                lines=("StockCode", "count"),
                is_cancel=("IsCancelled", "any"),
                is_guest=("IsGuest", "any"),
                CustomerID=("CustomerID", "first"),
                Country=("Country", "first"),
                hour=("Hour", "first"),
            )
            self.df_invoices = inv
            self.data_source = "production_parquet"
        else:
            self.df_invoices = _build_synthetic_invoice_corpus(seed=42)
            self.data_source = "synthetic_fallback"

        # Precompute customer cancellation propensity rates
        reg_custs = self.df_invoices[
            (~self.df_invoices["is_guest"]) & (self.df_invoices["CustomerID"].astype(str) != "None")
        ]
        if len(reg_custs) > 0:
            cust_stats = reg_custs.groupby(reg_custs["CustomerID"].astype(str))["is_cancel"].mean()
            self.customer_cancel_rates = cust_stats.to_dict()

        # Baseline distribution statistics for explainable Z-score triggers
        non_cancel_rev = self.df_invoices.loc[~self.df_invoices["is_cancel"], "rev"].abs()
        non_cancel_qty = self.df_invoices.loc[~self.df_invoices["is_cancel"], "qty"].abs()
        self.baseline_stats = {
            "rev_mean": float(non_cancel_rev.mean()) if len(non_cancel_rev) else 500.0,
            "rev_std": max(1.0, float(non_cancel_rev.std())) if len(non_cancel_rev) else 650.0,
            "rev_p99": float(non_cancel_rev.quantile(0.99)) if len(non_cancel_rev) else 4500.0,
            "qty_mean": float(non_cancel_qty.mean()) if len(non_cancel_qty) else 250.0,
            "qty_std": max(1.0, float(non_cancel_qty.std())) if len(non_cancel_qty) else 350.0,
        }

        # Fit Isolation Forest on sampled invoice feature vectors for fast inference
        fit_df = self.df_invoices
        if len(fit_df) > 12000:
            fit_df = fit_df.sample(n=12000, random_state=42)

        feat_matrix = _featurize_invoices(fit_df)
        x_scaled = self.scaler.fit_transform(feat_matrix[FEATURE_COLS])
        self.iso_forest.fit(x_scaled)

    def score_transaction(
        self,
        amount_gbp: float,
        total_units: int,
        line_items: int = 5,
        customer_id: str = "Guest",
        country: str = "United Kingdom",
        hour_of_day: float = 12.0,
        is_guest: bool = False,
        is_cancelled: bool = False,
        historical_cancel_rate: Optional[float] = None,
        invoice_no: Optional[str] = None,
        auto_quarantine: bool = False,
    ) -> Dict[str, Any]:
        """
        Scores a single invoice/order for anomaly, fraud, and cancellation risk [0..100].
        """
        abs_rev = abs(float(amount_gbp))
        abs_qty = max(1, abs(int(total_units)))
        lines = max(1, int(line_items))
        avg_price = max(0.05, abs_rev / abs_qty)
        is_off_hours = 1.0 if (hour_of_day < 6.0 or hour_of_day >= 22.0) else 0.0
        guest_flag = 1.0 if is_guest else 0.0

        vec = pd.DataFrame([{
            "log_abs_amount": math.log1p(abs_rev),
            "log1p_units": math.log1p(abs_qty),
            "line_items": float(lines),
            "log1p_avg_price": math.log1p(avg_price),
            "is_off_hours": is_off_hours,
            "is_guest": guest_flag,
        }])[FEATURE_COLS]

        x_scaled = self.scaler.transform(vec)
        # decision_function: negative => anomalous, positive => normal
        iso_raw_score = float(self.iso_forest.decision_function(x_scaled)[0])
        is_iso_anomaly = bool(self.iso_forest.predict(x_scaled)[0] == -1)

        # Map Isolation Forest score smoothly to [0..60] base contribution
        ml_component = 60.0 / (1.0 + math.exp(iso_raw_score * 8.5))

        # Interpretable business & statistical heuristic triggers [0..40]
        heuristic_pts = 0.0
        signals: List[str] = []

        rev_z = (abs_rev - self.baseline_stats["rev_mean"]) / self.baseline_stats["rev_std"]
        qty_z = (abs_qty - self.baseline_stats["qty_mean"]) / self.baseline_stats["qty_std"]

        if is_iso_anomaly:
            signals.append(f"Isolation Forest Structural Outlier (score={iso_raw_score:.3f})")

        if abs_rev > self.baseline_stats["rev_p99"] or rev_z >= 3.0:
            heuristic_pts += 18.0
            signals.append(f"Order value ₹{abs_rev:,.2f} exceeds 99th percentile (+{max(rev_z, 1.0):.1f}σ)")

        if qty_z >= 3.0 or (lines == 1 and abs_qty >= 500):
            heuristic_pts += 12.0
            signals.append(f"Extreme unit volume burst ({abs_qty:,} units across {lines} line item(s))")

        if is_guest and abs_rev >= 1500.0:
            heuristic_pts += 16.0
            signals.append(f"High-value unauthenticated guest checkout (₹{abs_rev:,.2f})")

        if is_off_hours > 0.0 and (abs_rev >= 1000.0 or is_guest):
            heuristic_pts += 10.0
            signals.append(f"Unusual off-hours checkout timestamp ({int(hour_of_day):02d}:00 UTC)")

        # Cancellation reversal / high customer cancel history
        clean_cid = str(customer_id).strip()
        cancel_rate = (
            historical_cancel_rate
            if historical_cancel_rate is not None
            else self.customer_cancel_rates.get(clean_cid, 0.0)
        )
        if is_cancelled or amount_gbp < 0:
            heuristic_pts += 14.0
            signals.append("Negative/cancelled adjustment invoice flag")
        if cancel_rate >= 0.25:
            heuristic_pts += min(20.0, cancel_rate * 25.0)
            signals.append(f"Elevated account historical cancellation rate ({cancel_rate * 100:.1f}%)")

        if not signals:
            signals.append("Transaction metrics consistent with normal baseline cluster")

        risk_score = round(min(99.5, max(2.0, ml_component + heuristic_pts)), 1)

        if risk_score >= 75.0:
            tier = "CRITICAL_QUARANTINE"
            action = "QUARANTINE_AND_HOLD"
        elif risk_score >= 50.0:
            tier = "HIGH_REVIEW"
            action = "STEP_UP_3DS_VERIFICATION"
        elif risk_score >= 30.0:
            tier = "ELEVATED_MONITOR"
            action = "LOG_AND_MONITOR"
        else:
            tier = "LOW_SAFE"
            action = "AUTO_APPROVE"

        inv_id = invoice_no or f"ORD-{secrets.token_hex(3).upper()}"
        result = {
            "invoice_no": inv_id,
            "customer_id": clean_cid,
            "country": country,
            "amount_gbp": round(float(amount_gbp), 2),
            "total_units": int(total_units),
            "line_items": lines,
            "risk_score": risk_score,
            "risk_tier": tier,
            "recommended_action": action,
            "isolation_forest_anomaly": is_iso_anomaly,
            "isolation_score": round(iso_raw_score, 4),
            "historical_cancel_rate_pct": round(cancel_rate * 100.0, 1),
            "triggered_signals": signals,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if auto_quarantine and risk_score >= 50.0:
            alert_id = f"FRD-{inv_id[-6:]}-{secrets.token_hex(2).upper()}"
            alert_item = {
                "alert_id": alert_id,
                **result,
                "status": "QUARANTINED",
            }
            AnomalyRegistry().enqueue_alert(alert_item)
            result["alert_id"] = alert_id

        return result

    def generate_anomaly_report(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Generates historical anomaly & cancellation intelligence plus live quarantine state."""
        if self._report_cache is None or force_refresh:
            df = self.df_invoices
            feats = _featurize_invoices(df)
            x_scaled = self.scaler.transform(feats[FEATURE_COLS])
            iso_scores = self.iso_forest.decision_function(x_scaled)

            scored_df = df.copy()
            scored_df["iso_score"] = iso_scores
            scored_df["abs_rev"] = scored_df["rev"].abs()

            total_inv = int(len(scored_df))
            cancel_cnt = int(scored_df["is_cancel"].sum())
            cancel_rate = round((cancel_cnt / max(1, total_inv)) * 100.0, 2)

            anomalous_mask = scored_df["iso_score"] < 0.0
            anomalous_df = scored_df[anomalous_mask].copy()
            flagged_cnt = int(len(anomalous_df))
            rev_at_risk = float(anomalous_df["abs_rev"].sum())

            top_anomalies_df = anomalous_df.sort_values(by=["iso_score", "abs_rev"], ascending=[True, False]).head(10)
            top_anomalies: List[Dict[str, Any]] = []
            for _, r in top_anomalies_df.iterrows():
                score_res = self.score_transaction(
                    amount_gbp=float(r["rev"]),
                    total_units=int(r["qty"]),
                    line_items=int(r["lines"]),
                    customer_id=str(r["CustomerID"]),
                    country=str(r["Country"]),
                    hour_of_day=float(r["hour"]) if pd.notna(r["hour"]) else 12.0,
                    is_guest=bool(r["is_guest"]),
                    is_cancelled=bool(r["is_cancel"]),
                    invoice_no=str(r["InvoiceNo"]),
                    auto_quarantine=False,
                )
                top_anomalies.append(score_res)

            # Top countries by invoice count & cancellation rate
            country_stats = (
                scored_df.groupby("Country", as_index=False)
                .agg(
                    total_invoices=("InvoiceNo", "count"),
                    cancelled_invoices=("is_cancel", "sum"),
                )
                .sort_values("total_invoices", ascending=False)
                .head(6)
            )
            country_breakdown = [
                {
                    "country": str(row["Country"]),
                    "total_invoices": int(row["total_invoices"]),
                    "cancelled_invoices": int(row["cancelled_invoices"]),
                    "cancellation_rate_pct": round(float(row["cancelled_invoices"]) / max(1, int(row["total_invoices"])) * 100.0, 2),
                }
                for _, row in country_stats.iterrows()
            ]

            self._report_cache = {
                "status": "success",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data_source": self.data_source,
                "model": "IsolationForest (100 Estimators, 5% Contamination) + Z-Score Rules",
                "summary": {
                    "total_invoices_scanned": total_inv,
                    "cancelled_invoices_count": cancel_cnt,
                    "cancellation_rate_pct": cancel_rate,
                    "flagged_anomalies_count": flagged_cnt,
                    "flagged_share_pct": round((flagged_cnt / max(1, total_inv)) * 100.0, 2),
                    "anomaly_revenue_exposure_gbp": round(rev_at_risk, 2),
                },
                "country_cancellation_rates": country_breakdown,
                "top_anomalous_invoices": top_anomalies,
            }

        report = dict(self._report_cache)
        report["quarantine_queue"] = list(AnomalyRegistry().quarantine_queue)
        return report
