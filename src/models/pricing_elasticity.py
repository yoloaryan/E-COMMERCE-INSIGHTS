"""
Dynamic Pricing Elasticity, Margin Optimization & A/B Experimentation Engine.

Implements:
1. Merchandise categorization from transactional SKU descriptions.
2. Within-SKU demeaned log-log OLS price elasticity estimation:
   ln(Q_ij) - mean(ln(Q_i)) = epsilon * (ln(P_ij) - mean(ln(P_i)))
3. Isoelastic demand & gross profit optimization across price bands [-20%, +20%].
4. Two-proportion Z-test statistical power & sample size calculator with uneven holdout support.
5. Controlled A/B pricing experiment runner with confidence intervals and persistent ledger.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import math

import numpy as np
import pandas as pd
from scipy import stats


DATA_PROCESSED_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"

# Merchandise taxonomy keyword rules (order matters for specificity)
CATEGORY_RULES: List[Tuple[str, List[str], float]] = [
    ("Kitchen & Dining", ["CAKE", "TEACUP", "SAUCER", "MUG", "JAR", "BOWL", "PLATE", "CUTLERY", "LUNCH", "TEA", "COFFEE", "TIN", "KITCHEN", "BAKING"], 0.47),
    ("Home Decor & Lighting", ["HEART", "LIGHT", "CANDLE", "LANTERN", "HOLDER", "CLOCK", "FRAME", "MIRROR", "BIRD", "VASE", "WALL", "SIGN"], 0.44),
    ("Bags & Storage", ["BAG", "TOTE", "BASKET", "BOX", "STORAGE", "POUCH", "PURSE", "CASE", "CRATE", "CHEST"], 0.49),
    ("Seasonal & Party", ["CHRISTMAS", "BUNTING", "PARTY", "EASTER", "TREE", "BAUBLE", "GARLAND", "WREATH", "FLAG", "FAIRY"], 0.36),
    ("Stationery & Craft", ["CARD", "PAPER", "NOTEBOOK", "PEN", "TAPE", "WRAP", "CRAFT", "STICKER", "DOILY", "TAG", "RIBBON"], 0.34),
]
DEFAULT_CATEGORY = "General Giftware"
DEFAULT_COGS_RATIO = 0.43

# Empirical prior elasticities by category for Bayesian precision shrinkage when sample variance is sparse
CATEGORY_ELASTICITY_PRIORS: Dict[str, float] = {
    "Kitchen & Dining": -1.35,
    "Home Decor & Lighting": -1.52,
    "Bags & Storage": -1.24,
    "Seasonal & Party": -1.78,
    "Stationery & Craft": -1.62,
    "General Giftware": -1.40,
}

CATEGORY_BASELINE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Kitchen & Dining": {"avg_price": 2.24, "units": 845000, "revenue": 1892800.0, "skus": 820, "txns": 115000, "cogs": 0.47},
    "Home Decor & Lighting": {"avg_price": 1.90, "units": 980000, "revenue": 1862000.0, "skus": 940, "txns": 132000, "cogs": 0.44},
    "Bags & Storage": {"avg_price": 2.09, "units": 1240000, "revenue": 2591600.0, "skus": 610, "txns": 96000, "cogs": 0.49},
    "Seasonal & Party": {"avg_price": 1.46, "units": 620000, "revenue": 905200.0, "skus": 480, "txns": 64000, "cogs": 0.36},
    "Stationery & Craft": {"avg_price": 1.09, "units": 790000, "revenue": 861100.0, "skus": 520, "txns": 58000, "cogs": 0.34},
    "General Giftware": {"avg_price": 2.06, "units": 410000, "revenue": 844600.0, "skus": 430, "txns": 62000, "cogs": 0.43},
}


def categorize_product(description: Any) -> str:
    """Deterministically maps a product description into a retail category."""
    if not isinstance(description, str) or not description.strip():
        return DEFAULT_CATEGORY
    upper_desc = description.upper()
    for cat_name, keywords, _ in CATEGORY_RULES:
        if any(kw in upper_desc for kw in keywords):
            return cat_name
    return DEFAULT_CATEGORY


def get_category_cogs_ratio(category: str) -> float:
    """Returns default COGS ratio (cost / price) for a given retail category."""
    for cat_name, _, cogs in CATEGORY_RULES:
        if cat_name == category:
            return cogs
    return DEFAULT_COGS_RATIO


def classify_elasticity_regime(elasticity: float) -> str:
    """Classifies demand sensitivity regime from numeric elasticity coefficient."""
    abs_e = abs(elasticity)
    if abs_e > 1.10:
        return "Elastic (Volume Sensitive)"
    if abs_e >= 0.90:
        return "Unit Elastic (Balanced)"
    return "Inelastic (Pricing Power)"


def build_synthetic_pricing_dataset(seed: int = 42) -> pd.DataFrame:
    """
    Constructs a deterministic synthetic SKU-price-tier retail dataset used only
    when processed Parquet artifacts are absent (e.g., clean CI checkouts).
    """
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, Any]] = []

    for cat_name, prior_eps in CATEGORY_ELASTICITY_PRIORS.items():
        defaults = CATEGORY_BASELINE_DEFAULTS[cat_name]
        base_price = defaults["avg_price"]
        n_skus = 25
        for sku_idx in range(n_skus):
            sku_code = f"SIM_{cat_name[:3].upper()}_{sku_idx:03d}"
            sku_base_p = base_price * rng.uniform(0.65, 1.55)
            sku_base_q = max(4.0, (defaults["units"] / 2500.0) * rng.uniform(0.5, 1.8))

            # Generate 4 price tiers per SKU with true isoelastic response + mild noise
            for tier_mult in [0.85, 0.95, 1.05, 1.18]:
                p = round(sku_base_p * tier_mult, 2)
                noise = rng.normal(0.0, 0.06)
                q = max(1, int(round(sku_base_q * (tier_mult ** prior_eps) * math.exp(noise))))
                rows.append({
                    "StockCode": sku_code,
                    "Category": cat_name,
                    "UnitPrice": p,
                    "Quantity": q,
                    "TotalPrice": round(p * q, 2),
                })

    return pd.DataFrame(rows)


class PricingElasticityEngine:
    """
    Estimates category-level price elasticity, computes profit-maximizing price points,
    and simulates revenue/margin sensitivity curves.
    """

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or DATA_PROCESSED_PATH
        self.df_txns: Optional[pd.DataFrame] = None
        self.data_source: str = "unknown"
        self._report_cache: Optional[Dict[str, Any]] = None
        self._load_transactions()

    def _load_transactions(self):
        if self.data_path.exists():
            df = pd.read_parquet(
                self.data_path,
                columns=["StockCode", "Description", "Quantity", "UnitPrice", "TotalPrice", "IsCancelled"],
            )
            df = df[(df["IsCancelled"] == False) & (df["Quantity"] > 0) & (df["UnitPrice"] > 0.05) & (df["UnitPrice"] < 500.0) & (df["Quantity"] < 500)].copy()
            if len(df) > 0:
                df["Category"] = df["Description"].map(categorize_product)
                self.df_txns = df
                self.data_source = "production_parquet"
                return

        self.df_txns = build_synthetic_pricing_dataset(seed=42)
        self.data_source = "synthetic_fallback"

    @staticmethod
    def estimate_category_elasticity(df_cat: pd.DataFrame, category_name: str, min_sku_obs: int = 3) -> Dict[str, Any]:
        """
        Estimates own-price elasticity using within-SKU demeaned log-log OLS: panel fixed effects
        eliminate cross-SKU price-level confounding inside a category.
        """
        prior_e = CATEGORY_ELASTICITY_PRIORS.get(category_name, -1.40)

        # Aggregate to (StockCode, UnitPrice) price tiers to measure order quantity response per price point
        tier_df = (
            df_cat.assign(PriceRounded=df_cat["UnitPrice"].round(2))
            .groupby(["StockCode", "PriceRounded"], as_index=False)
            .agg(
                mean_qty=("Quantity", "mean"),
                obs_count=("Quantity", "count"),
            )
        )

        # Retain SKUs with sufficient price variance
        sku_counts = tier_df.groupby("StockCode")["PriceRounded"].transform("count")
        multi_price = tier_df[sku_counts >= 2].copy()

        # Optionally restrict to well-observed price tiers if plentiful
        filtered_multi = multi_price[multi_price["obs_count"] >= max(1, min_sku_obs // 2)]
        if len(filtered_multi) >= 20:
            multi_price = filtered_multi

        raw_ols = prior_e
        r_squared = 0.0
        p_value = 1.0
        pairs_used = int(len(multi_price))

        if pairs_used >= 6:
            multi_price["log_p"] = np.log(multi_price["PriceRounded"].clip(lower=0.01))
            multi_price["log_q"] = np.log(multi_price["mean_qty"].clip(lower=0.1))

            # Within-SKU demeaning (fixed effects)
            multi_price["dm_log_p"] = multi_price["log_p"] - multi_price.groupby("StockCode")["log_p"].transform("mean")
            multi_price["dm_log_q"] = multi_price["log_q"] - multi_price.groupby("StockCode")["log_q"].transform("mean")

            x = multi_price["dm_log_p"].to_numpy()
            y = multi_price["dm_log_q"].to_numpy()
            valid_mask = np.isfinite(x) & np.isfinite(y)
            x, y = x[valid_mask], y[valid_mask]

            if len(x) >= 6 and np.std(x) > 1e-6:
                reg = stats.linregress(x, y)
                if np.isfinite(reg.slope):
                    raw_ols = float(reg.slope)
                    r_squared = float(reg.rvalue ** 2) if np.isfinite(reg.rvalue) else 0.0
                    p_value = float(reg.pvalue) if np.isfinite(reg.pvalue) else 1.0

        # Empirical Bayes shrinkage balances observed within-SKU regression against retail category priors,
        # ensuring economically valid downward-sloping demand curves bounded in [-3.2, -0.35].
        if raw_ols >= -0.15:
            # Wholesale minimum-order bundle noise can produce positive naive OLS; shrink toward downward-sloping prior
            weight_obs = min(0.35, pairs_used / 2000.0)
            clamped_obs = max(-0.85, min(-0.35, raw_ols if raw_ols < 0 else -0.45))
            shrunk_e = weight_obs * clamped_obs + (1.0 - weight_obs) * prior_e
        else:
            # Negative empirical slope confirmed: weight heavily toward data scaled by R^2 & observation volume
            weight_obs = min(0.85, (pairs_used / 500.0) * (0.5 + 0.5 * min(1.0, r_squared * 3.0)))
            shrunk_e = weight_obs * raw_ols + (1.0 - weight_obs) * prior_e

        elasticity = float(np.round(np.clip(shrunk_e, -3.20, -0.35), 3))

        return {
            "elasticity_coefficient": elasticity,
            "raw_ols_elasticity": float(np.round(raw_ols, 3)),
            "r_squared": float(np.round(r_squared, 4)),
            "p_value": float(np.round(p_value, 5)),
            "price_tier_observations": pairs_used,
        }

    @staticmethod
    def simulate_isoelastic_point(
        base_price: float,
        base_units: float,
        cogs_ratio: float,
        elasticity: float,
        price_change_pct: float,
    ) -> Dict[str, float]:
        """
        Computes revenue, unit volume, and gross profit at a target price adjustment percentage
        under a constant-elasticity demand curve Q(P) = Q_0 * (P / P_0)^elasticity.
        """
        price_mult = max(0.20, 1.0 + (price_change_pct / 100.0))
        new_price = base_price * price_mult
        unit_cost = base_price * cogs_ratio

        demand_mult = price_mult ** elasticity
        proj_units = max(0.0, base_units * demand_mult)
        proj_rev = new_price * proj_units
        proj_profit = (new_price - unit_cost) * proj_units
        margin_pct = ((new_price - unit_cost) / new_price * 100.0) if new_price > 0 else 0.0

        return {
            "price_change_pct": float(round(price_change_pct, 2)),
            "unit_price_gbp": float(round(new_price, 2)),
            "projected_units": int(round(proj_units)),
            "revenue_gbp": float(round(proj_rev, 2)),
            "gross_profit_gbp": float(round(proj_profit, 2)),
            "margin_pct": float(round(margin_pct, 2)),
        }

    def generate_elasticity_report(self, min_sku_obs: int = 5, force_refresh: bool = False) -> Dict[str, Any]:
        """Generates full category-level elasticity metrics, baseline KPIs, and optimal price targets."""
        if self._report_cache is not None and not force_refresh and min_sku_obs == 5:
            return self._report_cache

        df = self.df_txns
        categories_out: List[Dict[str, Any]] = []

        # Preserve consistent category ordering
        ordered_cats = [c for c, _, _ in CATEGORY_RULES] + [DEFAULT_CATEGORY]
        present_cats = set(df["Category"].unique())

        for cat in ordered_cats:
            if cat not in present_cats:
                continue
            df_cat = df[df["Category"] == cat]
            est = self.estimate_category_elasticity(df_cat, cat, min_sku_obs=min_sku_obs)

            base_units = float(df_cat["Quantity"].sum())
            base_revenue = float(df_cat["TotalPrice"].sum())
            # Use volume-weighted average unit price so Price * Units == Total Revenue accurately
            base_price = (base_revenue / base_units) if base_units > 0 else float(df_cat["UnitPrice"].mean())
            cogs_ratio = get_category_cogs_ratio(cat)
            base_profit = base_revenue * (1.0 - cogs_ratio)

            # Sweep [-20%, +20%] in 1% steps to identify bounded profit-maximizing price change
            best_pt = None
            for delta_pct in range(-20, 21):
                pt = self.simulate_isoelastic_point(
                    base_price=base_price,
                    base_units=base_units,
                    cogs_ratio=cogs_ratio,
                    elasticity=est["elasticity_coefficient"],
                    price_change_pct=float(delta_pct),
                )
                if best_pt is None or pt["gross_profit_gbp"] > best_pt["gross_profit_gbp"]:
                    best_pt = pt

            uplift_gbp = best_pt["gross_profit_gbp"] - base_profit
            uplift_pct = (uplift_gbp / base_profit * 100.0) if base_profit > 0 else 0.0

            categories_out.append({
                "category": cat,
                "elasticity_coefficient": est["elasticity_coefficient"],
                "raw_ols_elasticity": est["raw_ols_elasticity"],
                "demand_regime": classify_elasticity_regime(est["elasticity_coefficient"]),
                "r_squared": est["r_squared"],
                "p_value": est["p_value"],
                "price_tier_observations": est["price_tier_observations"],
                "sku_count": int(df_cat["StockCode"].nunique()),
                "transaction_count": int(len(df_cat)),
                "baseline_avg_price_gbp": round(base_price, 2),
                "baseline_total_units": int(round(base_units)),
                "baseline_revenue_gbp": round(base_revenue, 2),
                "baseline_cogs_ratio": cogs_ratio,
                "baseline_gross_margin_gbp": round(base_profit, 2),
                "optimal_price_change_pct": best_pt["price_change_pct"],
                "optimal_price_gbp": best_pt["unit_price_gbp"],
                "projected_max_profit_gbp": best_pt["gross_profit_gbp"],
                "margin_uplift_gbp": round(uplift_gbp, 2),
                "margin_uplift_pct": round(uplift_pct, 2),
            })

        # Top revenue SKUs with category elasticity inheritance
        cat_e_map = {c["category"]: c["elasticity_coefficient"] for c in categories_out}
        cat_opt_map = {c["category"]: c["optimal_price_change_pct"] for c in categories_out}

        agg_spec: Dict[str, Any] = {
            "Category": ("Category", "first"),
            "avg_price": ("UnitPrice", "mean"),
            "total_units": ("Quantity", "sum"),
            "total_rev": ("TotalPrice", "sum"),
            "price_points": ("UnitPrice", "nunique"),
        }
        if "Description" in df.columns:
            agg_spec["Description"] = ("Description", "first")

        top_skus_df = (
            df.groupby("StockCode", as_index=False)
            .agg(**agg_spec)
            .sort_values("total_rev", ascending=False)
            .head(8)
        )

        top_skus: List[Dict[str, Any]] = []
        for _, row in top_skus_df.iterrows():
            cat_name = row["Category"]
            e_val = cat_e_map.get(cat_name, -1.4)
            opt_delta = cat_opt_map.get(cat_name, 0.0)
            avg_p = float(row["avg_price"])
            top_skus.append({
                "stock_code": str(row["StockCode"]),
                "description": str(row["Description"]) if "Description" in row else f"{cat_name} Item",
                "category": cat_name,
                "current_avg_price_gbp": round(avg_p, 2),
                "historical_revenue_gbp": round(float(row["total_rev"]), 2),
                "distinct_price_points": int(row["price_points"]),
                "inherited_elasticity": e_val,
                "recommended_delta_pct": opt_delta,
                "target_price_gbp": round(avg_p * (1.0 + opt_delta / 100.0), 2),
            })

        avg_e = float(np.mean([c["elasticity_coefficient"] for c in categories_out])) if categories_out else -1.4

        report = {
            "status": "success",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_source": self.data_source,
            "total_transactions_analyzed": int(len(df)),
            "total_skus_analyzed": int(df["StockCode"].nunique()),
            "avg_portfolio_elasticity": round(avg_e, 3),
            "categories": categories_out,
            "top_sensitive_skus": top_skus,
            "experiments_ledger": PricingExperimentRegistry().list_experiments(),
        }

        if min_sku_obs == 5:
            self._report_cache = report
        return report

    def resolve_category(self, category: str) -> Dict[str, Any]:
        """Resolves a category entry from the elasticity report or raises ValueError."""
        report = self.generate_elasticity_report()
        cat_match = next(
            (c for c in report["categories"] if c["category"].lower() == category.strip().lower()),
            None,
        )
        if cat_match is None:
            raise ValueError(f"Unknown product category: {category}")
        return cat_match

    def simulate_price_change(
        self,
        category: str = "Kitchen & Dining",
        price_change_pct: float = 0.0,
        cogs_ratio: Optional[float] = None,
        promo_discount_pct: float = 0.0,
        elasticity_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Simulates revenue, order unit volume, and gross profit across price adjustments [-20%, +20%]
        plus an exact requested price change point for interactive decision modeling.
        """
        cat_match = self.resolve_category(category)

        used_cat = cat_match["category"]
        used_elasticity = float(elasticity_override if elasticity_override is not None else cat_match["elasticity_coefficient"])
        used_cogs = float(cogs_ratio if cogs_ratio is not None else cat_match["baseline_cogs_ratio"])
        base_price = float(cat_match["baseline_avg_price_gbp"])
        base_units = float(cat_match["baseline_total_units"])

        # Effective net price delta after optional promotional discount overlay
        effective_pct = ((1.0 + price_change_pct / 100.0) * (1.0 - promo_discount_pct / 100.0) - 1.0) * 100.0

        baseline_pt = self.simulate_isoelastic_point(base_price, base_units, used_cogs, used_elasticity, 0.0)
        sim_pt = self.simulate_isoelastic_point(base_price, base_units, used_cogs, used_elasticity, effective_pct)

        # Build payoff curve across -20% to +20% (step 2%)
        curve: List[Dict[str, float]] = []
        best_pt = None
        for pct in range(-20, 21, 2):
            pt = self.simulate_isoelastic_point(base_price, base_units, used_cogs, used_elasticity, float(pct))
            curve.append(pt)
            if best_pt is None or pt["gross_profit_gbp"] > best_pt["gross_profit_gbp"]:
                best_pt = pt

        # Fine-grained optimum check (1% step)
        fine_best = best_pt
        for pct in range(-20, 21):
            pt = self.simulate_isoelastic_point(base_price, base_units, used_cogs, used_elasticity, float(pct))
            if pt["gross_profit_gbp"] > fine_best["gross_profit_gbp"]:
                fine_best = pt

        rev_delta = sim_pt["revenue_gbp"] - baseline_pt["revenue_gbp"]
        rev_delta_pct = (rev_delta / baseline_pt["revenue_gbp"] * 100.0) if baseline_pt["revenue_gbp"] > 0 else 0.0
        profit_delta = sim_pt["gross_profit_gbp"] - baseline_pt["gross_profit_gbp"]
        profit_delta_pct = (profit_delta / baseline_pt["gross_profit_gbp"] * 100.0) if baseline_pt["gross_profit_gbp"] > 0 else 0.0
        unit_delta_pct = ((sim_pt["projected_units"] - baseline_pt["projected_units"]) / baseline_pt["projected_units"] * 100.0) if baseline_pt["projected_units"] > 0 else 0.0

        if fine_best["price_change_pct"] > 0:
            recommendation = (
                f"{used_cat} shows pricing upside (ε={used_elasticity:.2f}): testing a +{fine_best['price_change_pct']:.0f}% "
                f"adjustment improves gross profit by +₹{fine_best['gross_profit_gbp'] - baseline_pt['gross_profit_gbp']:,.2f}."
            )
        elif fine_best["price_change_pct"] < 0:
            recommendation = (
                f"{used_cat} is demand-elastic (ε={used_elasticity:.2f}): a {fine_best['price_change_pct']:.0f}% "
                f"strategic discount unlocks volume growth worth +₹{fine_best['gross_profit_gbp'] - baseline_pt['gross_profit_gbp']:,.2f} gross margin."
            )
        else:
            recommendation = f"{used_cat} is currently operating at its margin-optimal equilibrium price (₹{base_price:.2f})."

        return {
            "status": "success",
            "category": used_cat,
            "demand_regime": classify_elasticity_regime(used_elasticity),
            "elasticity_used": used_elasticity,
            "cogs_ratio_used": used_cogs,
            "requested_price_change_pct": round(price_change_pct, 2),
            "promo_discount_pct": round(promo_discount_pct, 2),
            "effective_price_change_pct": round(effective_pct, 2),
            "baseline": {
                "avg_price_gbp": baseline_pt["unit_price_gbp"],
                "total_units": baseline_pt["projected_units"],
                "revenue_gbp": baseline_pt["revenue_gbp"],
                "gross_profit_gbp": baseline_pt["gross_profit_gbp"],
                "margin_pct": baseline_pt["margin_pct"],
            },
            "simulated": {
                "new_price_gbp": sim_pt["unit_price_gbp"],
                "projected_units": sim_pt["projected_units"],
                "projected_revenue_gbp": sim_pt["revenue_gbp"],
                "projected_gross_profit_gbp": sim_pt["gross_profit_gbp"],
                "margin_pct": sim_pt["margin_pct"],
                "unit_delta_pct": round(unit_delta_pct, 2),
                "revenue_delta_gbp": round(rev_delta, 2),
                "revenue_delta_pct": round(rev_delta_pct, 2),
                "profit_delta_gbp": round(profit_delta, 2),
                "profit_delta_pct": round(profit_delta_pct, 2),
            },
            "optimal_point": {
                "price_change_pct": fine_best["price_change_pct"],
                "optimal_price_gbp": fine_best["unit_price_gbp"],
                "max_gross_profit_gbp": fine_best["gross_profit_gbp"],
                "profit_gain_gbp": round(fine_best["gross_profit_gbp"] - baseline_pt["gross_profit_gbp"], 2),
                "revenue_at_optimal_gbp": fine_best["revenue_gbp"],
            },
            "payoff_curve": curve,
            "recommendation": recommendation,
        }


class PricingExperimentRegistry:
    """Singleton ledger tracking executed pricing A/B experiments across the session."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PricingExperimentRegistry, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.experiments: List[Dict[str, Any]] = []

    def record_experiment(self, exp: Dict[str, Any]):
        self.experiments.insert(0, exp)
        if len(self.experiments) > 25:
            self.experiments.pop()

    def list_experiments(self) -> List[Dict[str, Any]]:
        return list(self.experiments)


class ABExperimentEngine:
    """
    Statistical power calculator and two-arm A/B experiment evaluator for pricing tests.
    """

    @staticmethod
    def calculate_power_and_sample_size(
        baseline_conversion_rate: float = 0.045,
        minimum_detectable_effect_pct: float = 10.0,
        alpha: float = 0.05,
        power: float = 0.80,
        daily_traffic: int = 2500,
        holdout_ratio: float = 0.50,
    ) -> Dict[str, Any]:
        """
        Computes required sample size per arm (supporting uneven holdout splits)
        and estimated test runtime using standard two-proportion Z-test math.
        """
        p1 = min(0.95, max(0.001, baseline_conversion_rate))
        p2 = min(0.99, max(0.001, p1 * (1.0 + minimum_detectable_effect_pct / 100.0)))
        diff = abs(p2 - p1)
        if diff < 1e-6:
            diff = 1e-6

        # k = ratio of variant sample to control holdout sample (if holdout_ratio=0.20, control=20%, variant=80% -> k=4.0)
        holdout = min(0.90, max(0.10, holdout_ratio))
        treatment_share = 1.0 - holdout
        k = treatment_share / holdout

        z_alpha = float(stats.norm.ppf(1.0 - alpha / 2.0))
        z_beta = float(stats.norm.ppf(power))

        # Weighted pooled proportion
        p_bar = (p1 + k * p2) / (1.0 + k)
        term_null = z_alpha * math.sqrt(p_bar * (1.0 - p_bar) * (1.0 + 1.0 / k))
        term_alt = z_beta * math.sqrt(p1 * (1.0 - p1) + (p2 * (1.0 - p2)) / k)

        n_control = max(30, int(math.ceil(((term_null + term_alt) / diff) ** 2)))
        n_variant = max(30, int(math.ceil(n_control * k)))
        total_n = n_control + n_variant
        est_days = max(1, int(math.ceil(total_n / max(1, daily_traffic))))

        # Generate statistical power saturation curve across total traffic fractions
        power_curve: List[Dict[str, Any]] = []
        for mult in [0.2, 0.4, 0.6, 0.8, 1.0, 1.25, 1.5, 2.0]:
            nc = max(30, int(round(n_control * mult)))
            nv = max(30, int(round(n_variant * mult)))
            se_alt = math.sqrt(p1 * (1.0 - p1) / nc + p2 * (1.0 - p2) / nv)
            p_pool_s = (nc * p1 + nv * p2) / (nc + nv)
            se_null = math.sqrt(p_pool_s * (1.0 - p_pool_s) * (1.0 / nc + 1.0 / nv))
            z_crit = z_alpha * (se_null / se_alt) if se_alt > 0 else 1.96
            effect_z = diff / se_alt if se_alt > 0 else 0.0
            achieved = float(1.0 - stats.norm.cdf(z_crit - effect_z))
            power_curve.append({
                "total_visitors": nc + nv,
                "days": round((nc + nv) / max(1, daily_traffic), 1),
                "power_pct": round(min(99.9, max(5.0, achieved * 100.0)), 1),
            })

        return {
            "status": "success",
            "inputs": {
                "baseline_conversion_rate": round(p1, 5),
                "target_variant_conversion_rate": round(p2, 5),
                "minimum_detectable_effect_pct": round(minimum_detectable_effect_pct, 2),
                "alpha": alpha,
                "target_power": power,
                "daily_traffic": daily_traffic,
                "control_holdout_ratio": round(holdout, 2),
            },
            "sample_size_control": n_control,
            "sample_size_variant": n_variant,
            "total_sample_size": total_n,
            "estimated_duration_days": est_days,
            "power_curve": power_curve,
        }

    @classmethod
    def run_experiment(
        cls,
        experiment_name: str,
        category: str,
        price_change_pct: float = 5.0,
        holdout_pct: float = 20.0,
        sample_size: int = 10000,
        baseline_conversion_rate: float = 0.045,
        cogs_ratio: float = 0.58,
        seed: Optional[int] = 42,
        control_visitors: Optional[int] = None,
        control_conversions: Optional[int] = None,
        variant_visitors: Optional[int] = None,
        variant_conversions: Optional[int] = None,
        engine: Optional[PricingElasticityEngine] = None,
    ) -> Dict[str, Any]:
        """
        Executes or evaluates a two-arm pricing A/B experiment (Control Holdout vs Price Variant)
        and logs it in the experiment registry.
        """
        pricing_engine = engine or PricingElasticityEngine()
        cat_match = pricing_engine.resolve_category(category)

        used_cat = cat_match["category"]
        base_price = float(cat_match["baseline_avg_price_gbp"])
        elasticity = float(cat_match["elasticity_coefficient"])
        avg_basket_units = 8.5  # Representative multi-unit retail order depth
        ctrl_aov = round(base_price * avg_basket_units, 2)
        var_price = round(base_price * (1.0 + price_change_pct / 100.0), 2)
        var_aov = round(var_price * avg_basket_units, 2)
        unit_cost = base_price * cogs_ratio
        var_cogs_ratio = min(0.95, max(0.05, unit_cost / max(0.01, var_price)))

        if (
            control_visitors is not None
            and control_conversions is not None
            and variant_visitors is not None
            and variant_conversions is not None
        ):
            n_ctrl = int(control_visitors)
            c_ctrl = min(n_ctrl, max(0, int(control_conversions)))
            n_var = int(variant_visitors)
            c_var = min(n_var, max(0, int(variant_conversions)))
        else:
            holdout_frac = min(0.80, max(0.05, holdout_pct / 100.0))
            n_ctrl = max(50, int(round(sample_size * holdout_frac)))
            n_var = max(50, sample_size - n_ctrl)

            # True conversion response governed by category price elasticity
            price_ratio = max(0.25, 1.0 + price_change_pct / 100.0)
            cvr_mult = price_ratio ** elasticity
            true_var_cvr = min(0.95, max(0.002, baseline_conversion_rate * cvr_mult))

            rng = np.random.default_rng(seed if seed is not None else int(datetime.now().timestamp()))
            c_ctrl = int(rng.binomial(n_ctrl, baseline_conversion_rate))
            c_var = int(rng.binomial(n_var, true_var_cvr))

        cvr_ctrl = c_ctrl / max(1, n_ctrl)
        cvr_var = c_var / max(1, n_var)

        # Revenue and Gross Profit per arm
        rev_ctrl = round(c_ctrl * ctrl_aov, 2)
        rev_var = round(c_var * var_aov, 2)
        profit_ctrl = round(rev_ctrl * (1.0 - cogs_ratio), 2)
        profit_var = round(rev_var * (1.0 - var_cogs_ratio), 2)

        rpv_ctrl = rev_ctrl / max(1, n_ctrl)
        rpv_var = rev_var / max(1, n_var)
        ppv_ctrl = profit_ctrl / max(1, n_ctrl)
        ppv_var = profit_var / max(1, n_var)

        # Two-proportion Z-test for conversion rate difference
        p_pooled = (c_ctrl + c_var) / max(1, n_ctrl + n_var)
        se_pooled = math.sqrt(max(1e-12, p_pooled * (1.0 - p_pooled) * (1.0 / n_ctrl + 1.0 / n_var)))
        z_stat = (cvr_var - cvr_ctrl) / se_pooled
        p_val = float(2.0 * stats.norm.sf(abs(z_stat)))

        # Unpooled 95% CI on relative conversion uplift
        se_diff = math.sqrt(max(1e-12, (cvr_ctrl * (1.0 - cvr_ctrl)) / n_ctrl + (cvr_var * (1.0 - cvr_var)) / n_var))
        diff_cvr = cvr_var - cvr_ctrl
        ci_lower_abs = diff_cvr - 1.96 * se_diff
        ci_upper_abs = diff_cvr + 1.96 * se_diff

        rel_cvr_uplift = ((cvr_var - cvr_ctrl) / cvr_ctrl * 100.0) if cvr_ctrl > 0 else 0.0
        rel_ppv_uplift = ((ppv_var - ppv_ctrl) / ppv_ctrl * 100.0) if ppv_ctrl > 0 else 0.0
        ci_lower_pct = (ci_lower_abs / cvr_ctrl * 100.0) if cvr_ctrl > 0 else 0.0
        ci_upper_pct = (ci_upper_abs / cvr_ctrl * 100.0) if cvr_ctrl > 0 else 0.0

        # Post-hoc achieved power
        effect_z = abs(diff_cvr) / se_diff if se_diff > 0 else 0.0
        achieved_power = float(min(0.999, max(0.05, 1.0 - stats.norm.cdf(1.96 - effect_z))))

        is_sig = bool(p_val < 0.05)
        if is_sig and ppv_var > ppv_ctrl:
            winner = "VARIANT"
            verdict = f"Statistically significant profit uplift (+{rel_ppv_uplift:.2f}%/visitor, p={p_val:.4f}). Ship new price!"
        elif is_sig and ppv_ctrl >= ppv_var:
            winner = "CONTROL"
            verdict = f"Control outperformed pricing variant (p={p_val:.4f}, {rel_ppv_uplift:+.2f}% profit/visitor). Keep baseline price."
        else:
            winner = "INCONCLUSIVE"
            verdict = f"Difference not yet statistically significant (p={p_val:.4f} ≥ 0.05). Extend experiment traffic."

        exp_record = {
            "experiment_id": f"EXP-{int(datetime.now(timezone.utc).timestamp() * 1000) % 1000000:06d}",
            "experiment_name": experiment_name,
            "category": used_cat,
            "elasticity_used": elasticity,
            "price_change_pct": round(price_change_pct, 2),
            "holdout_pct": round(holdout_pct, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "control": {
                "visitors": n_ctrl,
                "conversions": c_ctrl,
                "conversion_rate_pct": round(cvr_ctrl * 100.0, 2),
                "unit_price_gbp": round(base_price, 2),
                "aov_gbp": ctrl_aov,
                "revenue_gbp": rev_ctrl,
                "gross_profit_gbp": profit_ctrl,
                "revenue_per_visitor_gbp": round(rpv_ctrl, 2),
                "profit_per_visitor_gbp": round(ppv_ctrl, 2),
            },
            "variant": {
                "visitors": n_var,
                "conversions": c_var,
                "conversion_rate_pct": round(cvr_var * 100.0, 2),
                "unit_price_gbp": var_price,
                "aov_gbp": var_aov,
                "revenue_gbp": rev_var,
                "gross_profit_gbp": profit_var,
                "revenue_per_visitor_gbp": round(rpv_var, 2),
                "profit_per_visitor_gbp": round(ppv_var, 2),
            },
            "statistics": {
                "z_statistic": round(z_stat, 4),
                "p_value": round(p_val, 5),
                "statistically_significant": is_sig,
                "achieved_power_pct": round(achieved_power * 100.0, 1),
                "relative_cvr_uplift_pct": round(rel_cvr_uplift, 2),
                "relative_profit_per_visitor_uplift_pct": round(rel_ppv_uplift, 2),
                "ci_95_cvr_uplift_pct": [round(ci_lower_pct, 2), round(ci_upper_pct, 2)],
                "winner": winner,
                "verdict": verdict,
            },
        }

        PricingExperimentRegistry().record_experiment(exp_record)
        return {"status": "success", "experiment": exp_record}
