"""
Autonomous Telemetry Watchdog & Cross-Engine Digest Scheduler (Phase 20).

Performs unified health sweeps across all core Nexus Retail AI subsystems:
1. Inventory & Supply Chain EOQ Engine (critical stockouts <= ROP)
2. Cohort Retention & RFM Migration Engine (Champion slippage & M1 drop)
3. Enterprise MLOps Drift Monitor (PSI / Kolmogorov-Smirnov decay)
4. Transaction Fraud & Anomaly Registry (unresolved quarantine backlog)

Computes a composite Executive Health Score (0-100), prioritizes actionable
remediation directives with deep-link tab targets, and supports periodic
non-blocking FastAPI background sweeps when enabled.
"""

import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.api.campaigns import WatchdogEvaluator
from src.models.anomaly_detection import AnomalyRegistry
from src.models.cohort_analytics import get_cohort_engine
from src.models.drift_monitor import DataDriftMonitor
from src.models.inventory_optimization import get_inventory_engine


class AutonomousWatchdogEngine:
    """Singleton coordinator for cross-engine telemetry sweeps and executive digests."""

    def __init__(self):
        self.enabled: bool = True
        self.interval_seconds: int = 300
        self.last_sweep_at: Optional[str] = None
        self.sweep_history: List[Dict[str, Any]] = []
        self.latest_report: Optional[Dict[str, Any]] = None

    def configure(
        self,
        enabled: Optional[bool] = None,
        interval_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        if enabled is not None:
            self.enabled = bool(enabled)
        if interval_seconds is not None:
            self.interval_seconds = max(15, min(3600, int(interval_seconds)))
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "last_sweep_at": self.last_sweep_at,
        }

    def run_sweep(
        self,
        simulate_stress: bool = False,
        auto_remediate: bool = False,
        actor: str = "watchdog-scheduler",
    ) -> Dict[str, Any]:
        """Executes a synchronous 4-subsystem operational sweep and scores platform health."""
        inv_report = get_inventory_engine().generate_optimization_report(
            service_level=0.95, lead_time_days=7
        )
        mig_report = get_cohort_engine().generate_migration_report()
        drift_scenario = "black_friday" if simulate_stress else "baseline"
        drift_report = DataDriftMonitor().generate_drift_report(scenario=drift_scenario)
        quarantine_items = AnomalyRegistry().quarantine_queue

        # 1. Inventory & Stockout Risk evaluation
        crit_skus = int(inv_report["kpis"]["critical_reorder_skus"])
        overstock_cap = float(inv_report["kpis"]["overstock_capital_gbp"])
        if simulate_stress:
            crit_skus = max(crit_skus, 5)
        inv_status = "CRITICAL" if crit_skus >= 4 else ("WARNING" if crit_skus >= 2 else "HEALTHY")

        # 2. Cohort & Champion Slippage evaluation
        slipped_cnt = int(mig_report["summary"]["champions_slipped_count"])
        stay_rate = float(mig_report["summary"]["champion_stay_rate_pct"])
        if simulate_stress:
            stay_rate = min(stay_rate, 58.0)
        cohort_status = "CRITICAL" if stay_rate < 60.0 else ("WARNING" if slipped_cnt > 100 or stay_rate < 75.0 else "HEALTHY")

        # 3. MLOps Feature Drift evaluation
        drift_overall = str(drift_report.get("overall_status", "HEALTHY"))
        drift_cnt = int(drift_report.get("drift_detected_count", 0))
        drift_status = "CRITICAL" if drift_overall == "DRIFT_DETECTED" else ("WARNING" if drift_overall == "WARNING" else "HEALTHY")

        # 4. Fraud Quarantine Backlog evaluation
        pending_fraud = [item for item in quarantine_items if item.get("status") == "QUARANTINED"]
        pending_exposure = round(sum(float(item.get("amount_gbp", 0.0)) for item in pending_fraud), 2)
        fraud_status = "CRITICAL" if len(pending_fraud) >= 3 or pending_exposure >= 100000.0 else (
            "WARNING" if len(pending_fraud) >= 1 else "HEALTHY"
        )

        # Compute calibrated Executive Health Score (0-100)
        penalties = 0.0
        penalties += min(28.0, crit_skus * 4.5)
        penalties += 18.0 if cohort_status == "CRITICAL" else (8.0 if cohort_status == "WARNING" else 0.0)
        penalties += 26.0 if drift_status == "CRITICAL" else (10.0 if drift_status == "WARNING" else 0.0)
        penalties += min(24.0, len(pending_fraud) * 6.5)
        health_score = round(max(12.0, min(100.0, 100.0 - penalties)), 1)

        directives: List[Dict[str, Any]] = []
        if crit_skus > 0:
            directives.append({
                "id": f"DIR-INV-{crit_skus}",
                "severity": "CRITICAL" if crit_skus >= 4 else "WARNING",
                "subsystem": "Inventory EOQ",
                "title": f"{crit_skus} SKUs at or below Safety Stock / ROP",
                "detail": f"Auto-EOQ replenishment advised; ₹{overstock_cap:,.0f} also tied in overstock (>75d cover).",
                "target_tab": "inventory-mart",
                "cta_label": "Open EOQ Optimizer",
            })

        if drift_status != "HEALTHY":
            directives.append({
                "id": f"DIR-MLOPS-{drift_scenario.upper()}",
                "severity": drift_status,
                "subsystem": "MLOps Drift Radar",
                "title": f"Distribution shift across {drift_cnt} model feature(s)",
                "detail": f"Drift scenario '{drift_scenario}' crossed PSI alert bounds; retrain inference weights.",
                "target_tab": "admin-ops",
                "cta_label": "Inspect Drift & Retrain",
            })

        if len(pending_fraud) > 0:
            directives.append({
                "id": f"DIR-FRD-{len(pending_fraud)}",
                "severity": fraud_status,
                "subsystem": "Fraud Quarantine",
                "title": f"{len(pending_fraud)} unresolved transaction hold(s) (₹{pending_exposure:,.0f})",
                "detail": "Isolation Forest flagged anomalies awaiting Supply VP or Principal Admin triage.",
                "target_tab": "fraud-radar",
                "cta_label": "Triage Fraud Queue",
            })

        if cohort_status != "HEALTHY":
            directives.append({
                "id": "DIR-COHORT-SLIP",
                "severity": cohort_status,
                "subsystem": "Cohort Migration",
                "title": f"{slipped_cnt} Champion accounts migrated down ({stay_rate}% stay rate)",
                "detail": "Launch targeted win-back voucher flow to recover slipping high-LTV cohort members.",
                "target_tab": "segmentation",
                "cta_label": "View Migration Matrix",
            })

        remediation_triggered = None
        if auto_remediate and drift_status == "CRITICAL":
            shifted_feats = [
                f["feature"] for f in drift_report.get("features", [])
                if f.get("psi", 0) >= 0.25
            ] or ["UnitPrice", "Quantity"]
            remediation_triggered = WatchdogEvaluator.evaluate_drift_watchdog(
                psi_score=0.34,
                shifted_features=shifted_feats,
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        self.last_sweep_at = now_iso

        snapshot = {
            "sweep_id": f"SWP-{secrets.token_hex(3).upper()}",
            "timestamp": now_iso,
            "actor": actor,
            "stress_mode": simulate_stress,
            "health_score": health_score,
            "overall_status": (
                "CRITICAL" if health_score < 60.0 else ("ATTENTION" if health_score < 85.0 else "HEALTHY")
            ),
            "subsystems": [
                {
                    "key": "inventory",
                    "name": "Inventory & Stockout",
                    "status": inv_status,
                    "metric": f"{crit_skus} SKUs <= ROP",
                },
                {
                    "key": "cohorts",
                    "name": "Cohort Retention",
                    "status": cohort_status,
                    "metric": f"{stay_rate}% Champion Stay",
                },
                {
                    "key": "drift",
                    "name": "MLOps Drift PSI",
                    "status": drift_status,
                    "metric": f"{drift_cnt} Shifted Features",
                },
                {
                    "key": "fraud",
                    "name": "Fraud Quarantine",
                    "status": fraud_status,
                    "metric": f"{len(pending_fraud)} Pending Holds",
                },
            ],
            "directives": directives,
            "remediation_triggered": remediation_triggered,
        }

        self.latest_report = snapshot
        self.sweep_history.insert(0, {
            "sweep_id": snapshot["sweep_id"],
            "timestamp": snapshot["timestamp"],
            "health_score": snapshot["health_score"],
            "overall_status": snapshot["overall_status"],
            "directive_count": len(directives),
            "stress_mode": simulate_stress,
        })
        if len(self.sweep_history) > 30:
            self.sweep_history.pop()

        return snapshot

    def get_status(self) -> Dict[str, Any]:
        if self.latest_report is None:
            self.run_sweep(simulate_stress=False, auto_remediate=False, actor="system-init")
        return {
            "status": "online",
            "scheduler": {
                "enabled": self.enabled,
                "interval_seconds": self.interval_seconds,
                "last_sweep_at": self.last_sweep_at,
            },
            "latest": self.latest_report,
            "history": self.sweep_history[:12],
        }


_WATCHDOG_SINGLETON: Optional[AutonomousWatchdogEngine] = None


def get_watchdog_engine() -> AutonomousWatchdogEngine:
    """Returns process-wide singleton AutonomousWatchdogEngine instance."""
    global _WATCHDOG_SINGLETON
    if _WATCHDOG_SINGLETON is None:
        _WATCHDOG_SINGLETON = AutonomousWatchdogEngine()
    return _WATCHDOG_SINGLETON
