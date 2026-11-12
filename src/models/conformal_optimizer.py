"""
Split-Conformal Demand Uncertainty Engine (P10 / P50 / P90) & KKT Budget Optimizer (Phase 30).

Provides:
1. Finite-sample Split-Conformal Prediction Intervals over Random Forest out-of-sample
   daily revenue forecasts (normalized heteroscedastic nonconformity scores across
   calibration/evaluation folds, empirical coverage %, and Working-Capital VaR reserve).
2. Exact KKT Water-Filling Marketing Budget Allocator under diminishing-returns
   Michaelis-Menten cohort response curves R_s(b_s) = M_s * b_s / (b_s + K_s),
   enforcing both total budget cap and CFO minimum marginal ROI hurdle rate.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

FORECAST_RESULTS_PATH = ROOT_DIR / "data" / "processed" / "sales_forecast_results.csv"

COHORT_RESPONSE_CURVES = [
    {
        "segment": "Persuadables (High CATE)",
        "accounts": 412,
        "saturation_margin_inr": 620000.0,
        "half_saturation_spend_inr": 65000.0,
        "baseline_conversion_pct": 14.8,
        "channel_strategy": "Targeted 10-15% Win-Back Voucher + Personal Bundle",
    },
    {
        "segment": "At-Risk / Lapsing VIPs",
        "accounts": 248,
        "saturation_margin_inr": 485000.0,
        "half_saturation_spend_inr": 58000.0,
        "baseline_conversion_pct": 11.2,
        "channel_strategy": "Concierge Phone Outreach + Priority Shipping",
    },
    {
        "segment": "Loyal Repeat Core",
        "accounts": 844,
        "saturation_margin_inr": 310000.0,
        "half_saturation_spend_inr": 72000.0,
        "baseline_conversion_pct": 18.4,
        "channel_strategy": "Cross-Sell Apriori Bundle & Early Collection Access",
    },
    {
        "segment": "Occasional / Hibernating",
        "accounts": 1602,
        "saturation_margin_inr": 145000.0,
        "half_saturation_spend_inr": 95000.0,
        "baseline_conversion_pct": 3.6,
        "channel_strategy": "Low-Cost Automated Lifecycle Re-engagement",
    },
]


def _synthetic_forecast_df(n_days: int = 60, seed: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2011-10-10", periods=n_days, freq="D")
    base = 34000.0 + 9500.0 * np.sin(np.linspace(0, 4 * math.pi, n_days))
    preds = np.clip(base + rng.normal(0, 2200, size=n_days), 8500.0, 95000.0)
    noise = rng.normal(0, 0.16, size=n_days) * preds
    actuals = np.clip(preds + noise, 4000.0, 115000.0)
    return pd.DataFrame({
        "Date": dates.strftime("%Y-%m-%d"),
        "ActualRevenue": np.round(actuals, 2),
        "Pred_Random Forest Regressor": np.round(preds, 2),
    })


class ConformalOptimizerEngine:
    """Split-Conformal Forecast Calibration + Concave KKT Marketing Budget Optimizer."""

    def __init__(self, forecast_path: Path = FORECAST_RESULTS_PATH):
        self.forecast_path = forecast_path
        self.df = self._load_forecast_df()

    def _load_forecast_df(self) -> pd.DataFrame:
        if self.forecast_path.exists():
            try:
                raw = pd.read_csv(self.forecast_path)
                if {"Date", "ActualRevenue", "Pred_Random Forest Regressor"}.issubset(raw.columns) and len(raw) >= 16:
                    df = raw[["Date", "ActualRevenue", "Pred_Random Forest Regressor"]].dropna().copy()
                    df["Date"] = df["Date"].astype(str)
                    df["ActualRevenue"] = pd.to_numeric(df["ActualRevenue"], errors="coerce")
                    df["Pred_Random Forest Regressor"] = pd.to_numeric(df["Pred_Random Forest Regressor"], errors="coerce")
                    df = df.dropna().reset_index(drop=True)
                    if len(df) >= 16:
                        return df
            except Exception:
                pass
        return _synthetic_forecast_df()

    def compute_conformal_intervals(self, confidence_pct: float = 80.0) -> Dict[str, Any]:
        """
        Calibrates finite-sample normalized Split-Conformal prediction bands on out-of-sample
        residuals using the first 50% of validation dates for calibration and second 50% to
        audit empirical coverage.
        """
        conf = float(max(50.0, min(98.0, confidence_pct)))
        alpha = 1.0 - (conf / 100.0)

        y = self.df["ActualRevenue"].to_numpy(dtype=float)
        y_hat = np.clip(self.df["Pred_Random Forest Regressor"].to_numpy(dtype=float), 1.0, None)
        dates = self.df["Date"].tolist()

        # Scale normalizing denominator to capture heteroscedastic holiday variance
        scale = np.maximum(12000.0, 0.65 * y_hat)
        scores = np.abs(y - y_hat) / scale

        n = len(scores)
        split = max(8, n // 2)
        cal_scores = scores[:split]
        eval_scores = scores[split:]

        n_cal = len(cal_scores)
        q_level = min(1.0, math.ceil((n_cal + 1) * (1.0 - alpha)) / n_cal)
        q_hat = float(np.quantile(cal_scores, q_level, method="higher") if hasattr(np, "quantile") else np.percentile(cal_scores, q_level * 100.0))

        half_widths = q_hat * scale
        lower = np.maximum(0.0, y_hat - half_widths)
        upper = y_hat + half_widths

        eval_covered = (y[split:] >= lower[split:]) & (y[split:] <= upper[split:])
        all_covered = (y >= lower) & (y <= upper)
        empirical_eval_cov = float(np.mean(eval_covered) * 100.0) if len(eval_covered) else float(np.mean(all_covered) * 100.0)

        mean_width = float(np.mean(upper - lower))
        total_expected_rev = float(np.sum(y_hat))
        downside_var_buffer = float(np.sum(np.maximum(0.0, y_hat - lower)))

        series = []
        for idx in range(n):
            series.append({
                "date": dates[idx],
                "fold": "Calibration" if idx < split else "Evaluation",
                "actual_inr": round(float(y[idx]), 2),
                "point_p50_inr": round(float(y_hat[idx]), 2),
                "lower_inr": round(float(lower[idx]), 2),
                "upper_inr": round(float(upper[idx]), 2),
                "covered": bool(all_covered[idx]),
            })

        return {
            "status": "healthy",
            "summary": {
                "target_confidence_pct": round(conf, 1),
                "empirical_eval_coverage_pct": round(empirical_eval_cov, 1),
                "calibration_days": int(split),
                "evaluation_days": int(n - split),
                "conformal_multiplier_q": round(q_hat, 4),
                "avg_interval_width_inr": round(mean_width, 2),
                "downside_var_reserve_inr": round(downside_var_buffer, 2),
                "horizon_expected_revenue_inr": round(total_expected_rev, 2),
                "lower_percentile_label": f"P{int(round((alpha / 2.0) * 100))}",
                "upper_percentile_label": f"P{int(round((1.0 - alpha / 2.0) * 100))}",
            },
            "series": series,
        }

    def optimize_marketing_budget(
        self,
        total_budget_inr: float = 250000.0,
        min_roi_multiple: float = 1.5,
    ) -> Dict[str, Any]:
        """
        Solves KKT water-filling optimization for concave saturation curves:
            max sum_s [ M_s * b_s / (b_s + K_s) ]
            s.t. sum_s b_s <= B, b_s >= 0, dR_s/db_s >= min_roi_multiple
        """
        budget = float(max(10000.0, min(5000000.0, total_budget_inr)))
        hurdle = float(max(1.0, min(6.0, min_roi_multiple)))

        def spend_at_lambda(lam: float) -> List[float]:
            out = []
            for seg in COHORT_RESPONSE_CURVES:
                m_val = seg["saturation_margin_inr"]
                k_val = seg["half_saturation_spend_inr"]
                b_s = max(0.0, math.sqrt((m_val * k_val) / max(1e-9, lam)) - k_val)
                out.append(b_s)
            return out

        def margin_for_segment(seg: Dict[str, Any], b_s: float) -> float:
            if b_s <= 0.0:
                return 0.0
            return seg["saturation_margin_inr"] * (b_s / (b_s + seg["half_saturation_spend_inr"]))

        # Check unconstrained demand at hurdle rate floor first
        at_hurdle = spend_at_lambda(hurdle)
        if sum(at_hurdle) <= budget:
            optimal_spends = at_hurdle
            shadow_lam = hurdle
        else:
            lo, hi = hurdle, 200.0
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if sum(spend_at_lambda(mid)) > budget:
                    lo = mid
                else:
                    hi = mid
            shadow_lam = 0.5 * (lo + hi)
            optimal_spends = spend_at_lambda(shadow_lam)

        # Clean 2-decimal allocation conserving budget
        allocated_spends = [round(b, 2) for b in optimal_spends]
        allocated_total = round(sum(allocated_spends), 2)
        if allocated_total > budget:
            excess = round(allocated_total - budget, 2)
            idx_max = int(np.argmax(allocated_spends))
            allocated_spends[idx_max] = round(max(0.0, allocated_spends[idx_max] - excess), 2)
            allocated_total = round(sum(allocated_spends), 2)
        unallocated_reserve = round(max(0.0, budget - allocated_total), 2)

        # Naive equal-split benchmark spending the exact same allocated_total across all 4 cohorts
        equal_share = round(allocated_total / len(COHORT_RESPONSE_CURVES), 2)
        equal_total_margin = 0.0
        opt_total_margin = 0.0
        allocations = []

        for seg, b_opt in zip(COHORT_RESPONSE_CURVES, allocated_spends):
            m_opt = margin_for_segment(seg, b_opt)
            m_eq = margin_for_segment(seg, equal_share)
            opt_total_margin += m_opt
            equal_total_margin += m_eq
            marginal_roas = (seg["saturation_margin_inr"] * seg["half_saturation_spend_inr"]) / ((b_opt + seg["half_saturation_spend_inr"]) ** 2)
            avg_roas = (m_opt / b_opt) if b_opt > 0 else 0.0
            allocations.append({
                "segment": seg["segment"],
                "accounts": seg["accounts"],
                "allocated_budget_inr": round(b_opt, 2),
                "budget_share_pct": round((b_opt / budget) * 100.0, 1) if budget else 0.0,
                "equal_split_budget_inr": equal_share,
                "expected_incremental_margin_inr": round(m_opt, 2),
                "avg_roas_x": round(avg_roas, 2),
                "marginal_roas_x": round(marginal_roas, 2),
                "channel_strategy": seg["channel_strategy"],
            })

        opt_total_margin = round(opt_total_margin, 2)
        equal_total_margin = round(equal_total_margin, 2)
        optimizer_lift = round(opt_total_margin - equal_total_margin, 2)
        net_profit_after_spend = round(opt_total_margin - allocated_total, 2)
        portfolio_roas = round(opt_total_margin / allocated_total, 2) if allocated_total > 0 else 0.0

        return {
            "status": "healthy",
            "summary": {
                "currency": "INR",
                "currency_symbol": "₹",
                "total_budget_inr": round(budget, 2),
                "allocated_budget_inr": allocated_total,
                "unallocated_reserve_inr": unallocated_reserve,
                "min_roi_hurdle_x": round(hurdle, 2),
                "shadow_marginal_roas_x": round(shadow_lam, 2),
                "optimal_incremental_margin_inr": opt_total_margin,
                "equal_split_margin_inr": equal_total_margin,
                "optimizer_gain_over_equal_inr": optimizer_lift,
                "net_profit_after_spend_inr": net_profit_after_spend,
                "portfolio_roas_x": portfolio_roas,
            },
            "allocations": allocations,
        }


_CONFORMAL_SINGLETON: Optional[ConformalOptimizerEngine] = None


def get_conformal_optimizer() -> ConformalOptimizerEngine:
    global _CONFORMAL_SINGLETON
    if _CONFORMAL_SINGLETON is None:
        _CONFORMAL_SINGLETON = ConformalOptimizerEngine()
    return _CONFORMAL_SINGLETON
