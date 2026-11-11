"""
Statistical Data Drift Detection & MLOps Governance Engine.

Monitors production feature distributions against baseline training distributions
using two complementary statistical methodologies:
1. Kolmogorov-Smirnov (KS) Test for continuous cumulative distribution drift.
2. Population Stability Index (PSI) for binned population divergence.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional


def calculate_psi(expected: np.ndarray, actual: np.ndarray, num_buckets: int = 10, epsilon: float = 1e-4) -> float:
    """
    Computes Population Stability Index (PSI) between expected and actual distributions.

    Rules of Thumb:
    - PSI < 0.10: No significant distribution change (Healthy).
    - 0.10 <= PSI < 0.25: Moderate shift; monitor and assess model accuracy (Warning).
    - PSI >= 0.25: Significant distributional shift; action required (Drift Detected).
    """
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Create quantile buckets based on expected (baseline) distribution
    percentiles = np.linspace(0, 100, num_buckets + 1)
    bucket_bounds = np.unique(np.percentile(expected, percentiles))
    if len(bucket_bounds) < 3:
        bucket_bounds = np.linspace(np.min(expected), np.max(expected), num_buckets + 1)
    bucket_bounds[0] = -np.inf
    bucket_bounds[-1] = np.inf

    # Calculate proportions in each bucket
    expected_counts = np.histogram(expected, bins=bucket_bounds)[0]
    actual_counts = np.histogram(actual, bins=bucket_bounds)[0]

    expected_pct = expected_counts / len(expected)
    actual_pct = actual_counts / len(actual)

    # Avoid zero division with smoothing epsilon
    expected_pct = np.where(expected_pct == 0, epsilon, expected_pct)
    actual_pct = np.where(actual_pct == 0, epsilon, actual_pct)

    # Re-normalize after epsilon injection
    expected_pct /= np.sum(expected_pct)
    actual_pct /= np.sum(actual_pct)

    psi_val = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(np.round(psi_val, 4))


def calculate_ks(expected: np.ndarray, actual: np.ndarray) -> Dict[str, float]:
    """
    Computes two-sample Kolmogorov-Smirnov test.
    Returns test statistic (maximum vertical distance between empirical CDFs) and p-value.
    """
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return {"ks_statistic": 0.0, "p_value": 1.0}

    res = stats.ks_2samp(expected, actual)
    return {
        "ks_statistic": float(np.round(res.statistic, 4)),
        "p_value": float(np.round(res.pvalue, 5))
    }


class DataDriftMonitor:
    """
    Evaluates drift across transactional and customer feature vectors.
    """
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or (ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet")
        self.baseline_df = None
        self._load_baseline()

    def _load_baseline(self):
        if self.data_path.exists():
            df = pd.read_parquet(self.data_path)
            # Use valid non-cancelled transactions
            self.baseline_df = df[(df["IsCancelled"] == False) & (df["Quantity"] > 0)].copy()
        else:
            # Fallback mock baseline if parquet is unbuilt
            np.random.seed(42)
            n = 5000
            self.baseline_df = pd.DataFrame({
                "UnitPrice": np.random.exponential(scale=3.5, size=n) + 0.5,
                "Quantity": np.random.geometric(p=0.15, size=n),
                "TotalPrice": np.random.exponential(scale=22.0, size=n) + 1.0,
            })

    def generate_drift_report(self, scenario: str = "baseline") -> Dict[str, Any]:
        """
        Generates statistical drift audit across production feature vectors.
        Supports scenarios: 'baseline', 'black_friday', 'inflation', 'dormancy_surge'.
        """
        if self.baseline_df is None or len(self.baseline_df) == 0:
            return {"error": "Baseline dataset unavailable"}

        # Draw a representative baseline sample of 4,000 transactions
        sample_size = min(4000, len(self.baseline_df))
        ref_df = self.baseline_df.sample(n=sample_size, random_state=42).copy()
        cur_df = self.baseline_df.sample(n=sample_size, random_state=101).copy()

        # Apply synthetic scenario transformations if specified
        scenario = scenario.lower().strip()
        scenario_descriptions = {
            "baseline": "Normal operational traffic matching training distribution.",
            "black_friday": "Holiday volume surge: order quantities +180%, total basket spend +120%.",
            "inflation": "Macro price elevation: unit catalog prices elevated by +45%.",
            "dormancy_surge": "Customer inactivity shift: extended dormancy across purchasing cohorts."
        }

        if scenario == "black_friday":
            cur_df["Quantity"] = np.round(cur_df["Quantity"] * np.random.uniform(2.2, 3.2, size=len(cur_df)))
            cur_df["TotalPrice"] = cur_df["Quantity"] * cur_df["UnitPrice"]
        elif scenario == "inflation":
            cur_df["UnitPrice"] = np.round(cur_df["UnitPrice"] * np.random.uniform(1.65, 2.25, size=len(cur_df)), 2)
            cur_df["TotalPrice"] = cur_df["Quantity"] * cur_df["UnitPrice"]
        elif scenario == "dormancy_surge":
            # For transaction-level surrogate, simulate skewed price distribution towards slow items
            cur_df["Quantity"] = np.maximum(1, np.round(cur_df["Quantity"] * 0.4))
            cur_df["TotalPrice"] = cur_df["Quantity"] * cur_df["UnitPrice"]

        features_to_monitor = [
            {"col": "UnitPrice", "label": "Unit Price (£)", "unit": "£"},
            {"col": "Quantity", "label": "Order Item Quantity", "unit": "units"},
            {"col": "TotalPrice", "label": "Total Order Spend (£)", "unit": "£"}
        ]

        feature_reports = []
        drift_count = 0
        warning_count = 0

        for feat in features_to_monitor:
            col = feat["col"]
            exp = ref_df[col].values
            act = cur_df[col].values

            ks = calculate_ks(exp, act)
            psi = calculate_psi(exp, act)

            # Determine feature status
            if psi >= 0.25 or ks["p_value"] < 0.005:
                status = "DRIFT_DETECTED"
                badge = "Critical Drift"
                color = "red"
                drift_count += 1
                rec = f"Significant distribution divergence (PSI {psi:.3f}, KS p < 0.005). Model retraining recommended."
            elif psi >= 0.10 or ks["p_value"] < 0.05:
                status = "WARNING"
                badge = "Minor Shift"
                color = "gold"
                warning_count += 1
                rec = f"Moderate distribution variation detected (PSI {psi:.3f}). Monitor inference error closely."
            else:
                status = "HEALTHY"
                badge = "Healthy"
                color = "green"
                rec = "Distribution is statistically consistent with baseline training data."

            feature_reports.append({
                "feature": col,
                "label": feat["label"],
                "unit": feat["unit"],
                "baseline_mean": float(np.round(np.mean(exp), 2)),
                "baseline_std": float(np.round(np.std(exp), 2)),
                "current_mean": float(np.round(np.mean(act), 2)),
                "current_std": float(np.round(np.std(act), 2)),
                "psi_score": psi,
                "ks_statistic": ks["ks_statistic"],
                "ks_p_value": ks["p_value"],
                "status": status,
                "badge": badge,
                "color": color,
                "recommendation": rec
            })

        overall_status = "DRIFT_DETECTED" if drift_count > 0 else "WARNING" if warning_count > 0 else "HEALTHY"
        system_action = (
            "TRIGGER RETRAINING: Automated model pipeline re-execution required."
            if overall_status == "DRIFT_DETECTED"
            else "EVALUATE TELEMETRY: Model health degraded but within tolerable inference bounds."
            if overall_status == "WARNING"
            else "SYSTEM OPTIMAL: All production feature vectors match baseline training distribution."
        )

        return {
            "scenario": scenario,
            "scenario_description": scenario_descriptions.get(scenario, "Custom stream analysis."),
            "evaluated_samples": len(cur_df),
            "baseline_samples": len(ref_df),
            "overall_status": overall_status,
            "system_action": system_action,
            "features_monitored_count": len(feature_reports),
            "drift_detected_count": drift_count,
            "warning_count": warning_count,
            "features": feature_reports
        }


if __name__ == "__main__":
    monitor = DataDriftMonitor()
    print("[Drift Monitor] Testing Baseline Report:")
    base = monitor.generate_drift_report("baseline")
    print(f"  Overall: {base['overall_status']}")
    for f in base['features']:
        print(f"  - {f['feature']}: PSI={f['psi_score']}, p-val={f['ks_p_value']} -> {f['status']}")

    print("\n[Drift Monitor] Testing Black Friday Surge:")
    bf = monitor.generate_drift_report("black_friday")
    print(f"  Overall: {bf['overall_status']}")
    for f in bf['features']:
        print(f"  - {f['feature']}: PSI={f['psi_score']}, p-val={f['ks_p_value']} -> {f['status']}")
