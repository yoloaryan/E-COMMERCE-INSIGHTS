"""
Causal Uplift Modeling & Campaign Incrementality Engine (Phase 26).

Implements:
1. T-Learner (Two-Model CATE Estimator: tau(x) = mu_1(x) - mu_0(x)) using
   scikit-learn GradientBoostingRegressor to score individual incremental spend lift.
2. 4-Quadrant Causal Segmentation:
   - Persuadables (high positive CATE -> target with voucher)
   - Sure Things (high baseline, low lift -> exclude to preserve promo margin)
   - Lost Causes (low baseline, flat response -> exclude to cut waste)
   - Sleeping Dogs (negative CATE -> suppress immediately)
3. Cumulative Qini / Profit Uplift Curve comparing T-Learner vs. Random Blanket Targeting.
4. Difference-in-Differences (DiD) Pre/Post Quasi-Experimental Attribution.
"""

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.models.customer_360 import Customer360Engine


class CausalUpliftEngine:
    """T-Learner CATE & Difference-in-Differences Attribution Engine."""

    def __init__(self, use_parquet: bool = True, seed: int = 26):
        self.seed = seed
        self.data_source: str = "synthetic_fallback"
        self.customer_panel: List[Dict[str, Any]] = []
        self._load_and_score_customers(use_parquet=use_parquet)

    def _load_and_score_customers(self, use_parquet: bool = True) -> None:
        c360 = Customer360Engine(use_parquet=use_parquet)
        self.data_source = c360.data_source
        raw_profiles = list(c360.profiles.values())

        # Keep up to top 800 active accounts by spend/recency mix for fast startup fitting
        sample_profiles = raw_profiles[:800] if len(raw_profiles) > 800 else raw_profiles
        if len(sample_profiles) < 25:
            sample_profiles = Customer360Engine(use_parquet=False).query_ledger(limit=100)["customers"]

        rng = np.random.default_rng(self.seed)
        n = len(sample_profiles)

        # Build numerical feature matrix X = [log1p(spend), log1p(orders), recency, aov, return_rate, churnProb]
        X = np.array([
            [
                math.log1p(max(0.0, float(p["spend"]))),
                math.log1p(max(0.0, float(p["orders"]))),
                float(p["recency"]),
                min(5000.0, float(p["aov"])),
                float(p.get("return_rate_pct", 0.0)),
                float(p["churnProb"]),
            ]
            for p in sample_profiles
        ], dtype=float)

        # Simulate historical randomized A/B promo training logs grounded in observed baseline RFM
        treatment = rng.binomial(1, 0.5, size=n)
        baseline_spend = np.clip(X[:, 3] * (1.2 + 0.25 * X[:, 1]) * (1.0 - 0.35 * X[:, 5]), 15.0, 2200.0)

        # Heterogeneous true uplift structure:
        # Mid-to-high value customers with rising recency (35-110d) respond strongest (+tau);
        # ultra-high returners or ultra-recent Champions either already buy or show promo fatigue
        rec = X[:, 2]
        ret = X[:, 4]
        persuasion_window = np.exp(-((rec - 68.0) ** 2) / (2.0 * (34.0 ** 2)))
        fatigue_penalty = np.where(ret > 14.0, -95.0, 0.0) - np.where(rec < 10.0, 18.0, 0.0)
        true_tau = (baseline_spend * 0.28 * persuasion_window) + fatigue_penalty + rng.normal(0, 12.0, size=n)

        y_obs = baseline_spend + treatment * true_tau + rng.normal(0, 18.0, size=n)
        y_obs = np.clip(y_obs, 0.0, 5000.0)

        # Fit T-Learner models mu_0(X) and mu_1(X)
        mask_t = treatment == 1
        mask_c = treatment == 0

        mu1 = GradientBoostingRegressor(n_estimators=45, max_depth=3, random_state=self.seed)
        mu0 = GradientBoostingRegressor(n_estimators=45, max_depth=3, random_state=self.seed + 1)
        mu1.fit(X[mask_t], y_obs[mask_t])
        mu0.fit(X[mask_c], y_obs[mask_c])

        pred_y1 = mu1.predict(X)
        pred_y0 = mu0.predict(X)
        cate = pred_y1 - pred_y0

        median_y0 = float(np.median(pred_y0))
        scored: List[Dict[str, Any]] = []
        for idx, p in enumerate(sample_profiles):
            tau_val = round(float(cate[idx]), 2)
            base_val = round(max(10.0, float(pred_y0[idx])), 2)
            if tau_val < -5.0:
                quadrant = "Sleeping Dogs"
            elif tau_val >= 35.0:
                quadrant = "Persuadables"
            elif base_val >= median_y0:
                quadrant = "Sure Things"
            else:
                quadrant = "Lost Causes"

            scored.append({
                "customer_id": str(p["id"]),
                "country": str(p.get("country", "United Kingdom")),
                "segment": str(p["segment"]),
                "recency_days": int(p["recency"]),
                "historical_spend_gbp": round(float(p["spend"]), 2),
                "baseline_expected_gbp": base_val,
                "predicted_treated_gbp": round(max(0.0, float(pred_y1[idx])), 2),
                "cate_uplift_gbp": tau_val,
                "uplift_pct": round((tau_val / max(1.0, base_val)) * 100.0, 1),
                "quadrant": quadrant,
            })

        scored.sort(key=lambda r: r["cate_uplift_gbp"], reverse=True)
        self.customer_panel = scored

    def simulate_targeting_policy(
        self,
        top_k_pct: float = 30.0,
        discount_pct: float = 15.0,
        gross_margin_rate: float = 0.42,
        contact_cost_gbp: float = 1.50,
    ) -> Dict[str, Any]:
        """Builds Qini/Uplift curves and compares Causal vs Blanket Promo Profit."""
        k_pct = max(5.0, min(100.0, float(top_k_pct)))
        disc = max(5.0, min(40.0, float(discount_pct)))
        total_n = max(1, len(self.customer_panel))

        # Per-customer net incremental profit if mailed a discount voucher
        def _net_profit(row: Dict[str, Any]) -> float:
            # Incremental gross margin minus discount dilution on baseline purchases + contact cost
            inc_margin = row["cate_uplift_gbp"] * gross_margin_rate
            cannibalization_cost = row["baseline_expected_gbp"] * (disc / 100.0) * 0.35
            return inc_margin - cannibalization_cost - contact_cost_gbp

        sorted_causal = self.customer_panel  # Already sorted by CATE descending
        avg_profit_all = float(np.mean([_net_profit(r) for r in sorted_causal]))

        curve: List[Dict[str, Any]] = []
        cum_causal = 0.0
        decile_targets = list(range(10, 101, 10))
        causal_profits = [_net_profit(r) for r in sorted_causal]

        for d in decile_targets:
            cutoff = max(1, int(round((d / 100.0) * total_n)))
            cum_causal = round(float(sum(causal_profits[:cutoff])), 2)
            rand_profit = round(avg_profit_all * cutoff, 2)
            curve.append({
                "pct_targeted": d,
                "label": f"Top {d}%",
                "causal_net_profit_gbp": cum_causal,
                "random_blanket_profit_gbp": rand_profit,
            })

        selected_n = max(1, int(round((k_pct / 100.0) * total_n)))
        causal_selected = sorted_causal[:selected_n]
        selected_profit = round(float(sum(causal_profits[:selected_n])), 2)
        blanket_profit = round(float(sum(causal_profits)), 2)

        # Quadrant summary
        quad_names = ["Persuadables", "Sure Things", "Lost Causes", "Sleeping Dogs"]
        quadrants: List[Dict[str, Any]] = []
        for qn in quad_names:
            members = [r for r in sorted_causal if r["quadrant"] == qn]
            cnt = len(members)
            avg_tau = round(float(np.mean([m["cate_uplift_gbp"] for m in members])), 2) if cnt else 0.0
            total_tau = round(float(sum(m["cate_uplift_gbp"] for m in members)), 2)
            quadrants.append({
                "quadrant": qn,
                "account_count": cnt,
                "share_pct": round((cnt / total_n) * 100.0, 1),
                "avg_cate_gbp": avg_tau,
                "total_uplift_gbp": total_tau,
                "recommended_policy": (
                    "Send Discount Voucher" if qn == "Persuadables"
                    else ("Withhold Discount (Save Margin)" if qn == "Sure Things"
                          else ("Suppress Marketing Spend" if qn == "Lost Causes" else "Do Not Contact (Negative Lift)"))
                ),
            })

        sure_things = next((q for q in quadrants if q["quadrant"] == "Sure Things"), None)
        saved_promo_margin = round(
            sum(
                r["baseline_expected_gbp"] * (disc / 100.0) * 0.35 + contact_cost_gbp
                for r in sorted_causal if r["quadrant"] == "Sure Things"
            ),
            2,
        )

        # Scale Pre/Post Difference-in-Differences benchmark
        did = self.compute_did_attribution(
            treat_pre=round(float(np.mean([r["baseline_expected_gbp"] for r in causal_selected])), 2),
            treat_post=round(float(np.mean([r["predicted_treated_gbp"] for r in causal_selected])), 2),
            ctrl_pre=round(float(np.mean([r["baseline_expected_gbp"] for r in sorted_causal[selected_n:] or sorted_causal])), 2),
            ctrl_post=round(float(np.mean([r["baseline_expected_gbp"] for r in sorted_causal[selected_n:] or sorted_causal]) * 1.015), 2),
            n_treat=selected_n,
            n_ctrl=max(10, total_n - selected_n),
        )

        return {
            "status": "healthy",
            "data_source": self.data_source,
            "model": "T-Learner (GradientBoostingRegressor Dual-Model CATE)",
            "parameters": {
                "top_k_pct": k_pct,
                "discount_pct": disc,
                "total_scored_accounts": total_n,
                "targeted_accounts": selected_n,
            },
            "summary": {
                "persuadable_count": next((q["account_count"] for q in quadrants if q["quadrant"] == "Persuadables"), 0),
                "sure_things_excluded_count": sure_things["account_count"] if sure_things else 0,
                "saved_promo_margin_gbp": saved_promo_margin,
                "causal_net_profit_gbp": selected_profit,
                "blanket_net_profit_gbp": blanket_profit,
                "incremental_advantage_gbp": round(selected_profit - blanket_profit, 2),
                "did_lift_pct": did["did_lift_pct"],
            },
            "quadrants": quadrants,
            "qini_curve": curve,
            "top_persuadables": [r for r in sorted_causal if r["quadrant"] == "Persuadables"][:10],
            "did_attribution": did,
        }

    @staticmethod
    def compute_did_attribution(
        treat_pre: float,
        treat_post: float,
        ctrl_pre: float,
        ctrl_post: float,
        n_treat: int = 250,
        n_ctrl: int = 250,
    ) -> Dict[str, Any]:
        """Computes Difference-in-Differences causal lift & approximate Wald significance."""
        treat_diff = treat_post - treat_pre
        ctrl_diff = ctrl_post - ctrl_pre
        did_effect = round(treat_diff - ctrl_diff, 2)
        did_lift_pct = round((did_effect / max(1.0, treat_pre + ctrl_diff)) * 100.0, 2)

        # Conservative pooled standard error estimator on revenue-per-account variance
        sigma_est = max(15.0, abs(treat_pre) * 0.42)
        se = math.sqrt((sigma_est ** 2 / max(2, n_treat)) + (sigma_est ** 2 / max(2, n_ctrl)))
        z_stat = did_effect / max(0.01, se)
        p_val = math.erfc(abs(z_stat) / math.sqrt(2.0))

        return {
            "treatment_pre_gbp": round(treat_pre, 2),
            "treatment_post_gbp": round(treat_post, 2),
            "control_pre_gbp": round(ctrl_pre, 2),
            "control_post_gbp": round(ctrl_post, 2),
            "did_effect_per_account_gbp": did_effect,
            "did_lift_pct": did_lift_pct,
            "z_statistic": round(z_stat, 2),
            "p_value": round(p_val, 5),
            "statistically_significant": bool(p_val < 0.05),
        }


_CAUSAL_ENGINE_SINGLETON: Optional[CausalUpliftEngine] = None


def get_causal_engine() -> CausalUpliftEngine:
    """Returns process-wide singleton CausalUpliftEngine instance."""
    global _CAUSAL_ENGINE_SINGLETON
    if _CAUSAL_ENGINE_SINGLETON is None:
        _CAUSAL_ENGINE_SINGLETON = CausalUpliftEngine()
    return _CAUSAL_ENGINE_SINGLETON

