"""
Market Basket Association Rules & Cross-Sell Bundle Optimizer (Phase 21).

Extracts empirical pairwise Support, Confidence, Lift, and Conviction metrics
across transaction baskets from UCI Online Retail Parquet data (with a deterministic
synthetic multi-basket fallback), and evaluates live shopping basket add-ons &
promotional bundle margin economics.
"""

from itertools import combinations
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

DATA_PROCESSED_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"

DEFAULT_META: Dict[str, Tuple[str, float]] = {
    "22423": ("Regency Cakestand 3 Tier", 10.95),
    "22699": ("Roses Regency Teacup And Saucer", 2.95),
    "22697": ("Green Regency Teacup And Saucer", 2.95),
    "22698": ("Pink Regency Teacup And Saucer", 2.95),
    "85123A": ("White Hanging Heart T-Light Holder", 2.55),
    "21733": ("Red Hanging Heart T-Light Holder", 2.55),
    "47566": ("Party Bunting", 4.65),
    "85099B": ("Jumbo Bag Red Retrospot", 1.79),
    "20725": ("Lunch Bag Red Retrospot", 1.65),
    "22386": ("Jumbo Bag Pink Polkadot", 1.95),
    "84879": ("Assorted Colour Bird Ornament", 1.69),
    "22720": ("Set Of 3 Cake Tins Pantry Design", 4.95),
}


def _build_synthetic_baskets(seed: int = 21) -> Tuple[List[set], Dict[str, Tuple[str, float]]]:
    """Deterministic multi-item transaction baskets preserving flagship co-purchases."""
    rng = np.random.default_rng(seed)
    clusters = [
        (["22423", "22699", "22697", "22698"], 0.72),
        (["85123A", "21733", "84879"], 0.66),
        (["85099B", "20725", "22386"], 0.68),
        (["47566", "22720", "22423"], 0.58),
    ]
    all_codes = list(DEFAULT_META.keys())
    baskets: List[set] = []

    for i in range(420):
        c_codes, prob = clusters[i % len(clusters)]
        basket = {c_codes[0]}
        for extra in c_codes[1:]:
            if rng.random() < prob:
                basket.add(extra)
        if rng.random() < 0.22:
            basket.add(all_codes[int(rng.integers(0, len(all_codes)))])
        baskets.append(basket)

    return baskets, dict(DEFAULT_META)


class MarketBasketEngine:
    """Computes Support/Confidence/Lift association rules & evaluates cart bundles."""

    def __init__(self, use_parquet: bool = True, max_top_skus: int = 45):
        self.data_source: str = "synthetic_fallback"
        self.baskets: List[set] = []
        self.sku_meta: Dict[str, Tuple[str, float]] = {}
        self.rules: List[Dict[str, Any]] = []
        self._load_baskets(use_parquet=use_parquet, max_top_skus=max_top_skus)
        self._mine_pairwise_rules()

    def _load_baskets(self, use_parquet: bool = True, max_top_skus: int = 45) -> None:
        if use_parquet and DATA_PROCESSED_PATH.exists():
            try:
                df = pd.read_parquet(
                    DATA_PROCESSED_PATH,
                    columns=["InvoiceNo", "StockCode", "Description", "Quantity", "UnitPrice"],
                )
                df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)].copy()
                df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()

                top_counts = df["StockCode"].value_counts().head(max_top_skus).index
                focus_codes = set(top_counts.tolist()) | set(DEFAULT_META.keys())
                sub = df[df["StockCode"].isin(focus_codes)]

                grouped_meta = sub.groupby("StockCode").agg(
                    desc=("Description", "first"),
                    price=("UnitPrice", "median"),
                )
                for code, row in grouped_meta.iterrows():
                    code_s = str(code)
                    if code_s in DEFAULT_META:
                        self.sku_meta[code_s] = DEFAULT_META[code_s]
                    else:
                        self.sku_meta[code_s] = (
                            str(row["desc"] or f"SKU {code_s}").strip()[:52].title(),
                            round(float(row["price"]), 2),
                        )

                inv_groups = sub.groupby("InvoiceNo")["StockCode"].apply(set)
                self.baskets = [b for b in inv_groups.tolist() if len(b) >= 2]
                if len(self.baskets) >= 20:
                    self.data_source = "parquet_historical"
                    return
            except Exception:
                pass

        self.baskets, self.sku_meta = _build_synthetic_baskets()
        self.data_source = "synthetic_fallback"

    def _mine_pairwise_rules(self) -> None:
        total_baskets = max(1, len(self.baskets))
        item_counts: Dict[str, int] = {}
        pair_counts: Dict[Tuple[str, str], int] = {}

        for b in self.baskets:
            ordered = sorted(b)
            for item in ordered:
                item_counts[item] = item_counts.get(item, 0) + 1
            for a, c in combinations(ordered, 2):
                pair_counts[(a, c)] = pair_counts.get((a, c), 0) + 1
                pair_counts[(c, a)] = pair_counts.get((c, a), 0) + 1

        rules: List[Dict[str, Any]] = []
        for (a, b), ab_cnt in pair_counts.items():
            a_cnt = item_counts.get(a, 0)
            b_cnt = item_counts.get(b, 0)
            if a_cnt < 5 or b_cnt < 5 or ab_cnt < 3:
                continue

            support = ab_cnt / float(total_baskets)
            supp_b = b_cnt / float(total_baskets)
            confidence = ab_cnt / float(a_cnt)
            lift = confidence / max(1e-6, supp_b)
            conviction = (1.0 - supp_b) / max(1e-4, 1.0 - min(0.9999, confidence))

            a_desc, a_price = self.sku_meta.get(a, (f"SKU {a}", 3.5))
            b_desc, b_price = self.sku_meta.get(b, (f"SKU {b}", 3.5))
            combined_price = round(a_price + b_price, 2)

            rules.append({
                "rule_id": f"{a}->{b}",
                "antecedent_code": a,
                "antecedent_name": a_desc,
                "antecedent_price": round(a_price, 2),
                "consequent_code": b,
                "consequent_name": b_desc,
                "consequent_price": round(b_price, 2),
                "co_occurrence_count": int(ab_cnt),
                "support_pct": round(support * 100.0, 2),
                "confidence_pct": round(confidence * 100.0, 1),
                "lift": round(lift, 2),
                "conviction": round(min(50.0, conviction), 2),
                "bundle_retail_gbp": combined_price,
                "bundle_offer_gbp": round(combined_price * 0.90, 2),
            })

        rules.sort(key=lambda r: (r["lift"], r["confidence_pct"], r["co_occurrence_count"]), reverse=True)
        self.rules = rules

    def generate_rules_report(
        self,
        min_lift: float = 1.2,
        min_support_pct: float = 0.5,
        limit: int = 18,
    ) -> Dict[str, Any]:
        """Filters association rules by lift & support thresholds."""
        ml = max(0.5, float(min_lift))
        ms = max(0.0, float(min_support_pct))
        lim = max(1, min(100, int(limit)))

        filtered = [
            r for r in self.rules
            if r["lift"] >= ml and r["support_pct"] >= ms
        ][:lim]

        top_lift = filtered[0]["lift"] if filtered else (self.rules[0]["lift"] if self.rules else 1.0)
        avg_conf = round(float(np.mean([r["confidence_pct"] for r in filtered])), 1) if filtered else 0.0
        avg_bundle_val = round(float(np.mean([r["bundle_offer_gbp"] for r in filtered])), 2) if filtered else 0.0

        return {
            "status": "healthy",
            "data_source": self.data_source,
            "total_baskets_mined": len(self.baskets),
            "filters": {"min_lift": ml, "min_support_pct": ms, "limit": lim},
            "summary": {
                "total_matching_rules": len(filtered),
                "total_catalog_rules": len(self.rules),
                "top_lift": top_lift,
                "avg_confidence_pct": avg_conf,
                "avg_bundle_offer_gbp": avg_bundle_val,
            },
            "rules": filtered,
        }

    def evaluate_bundle(self, items: List[str], discount_pct: float = 10.0) -> Dict[str, Any]:
        """Scores an active shopping basket and returns highest-Lift complementary SKUs & margin math."""
        clean_items = [str(x).strip().upper() for x in items if str(x).strip()]
        item_set = set(clean_items)
        disc = max(0.0, min(40.0, float(discount_pct)))

        base_subtotal = round(sum(self.sku_meta.get(c, (c, 3.5))[1] for c in clean_items), 2)

        # Find highest-Lift consequents not already in the cart
        candidates: Dict[str, Dict[str, Any]] = {}
        for rule in self.rules:
            if rule["antecedent_code"] in item_set and rule["consequent_code"] not in item_set:
                target = rule["consequent_code"]
                if target not in candidates or rule["lift"] > candidates[target]["lift"]:
                    candidates[target] = {
                        "stock_code": target,
                        "description": rule["consequent_name"],
                        "unit_price": rule["consequent_price"],
                        "triggered_by": rule["antecedent_code"],
                        "confidence_pct": rule["confidence_pct"],
                        "lift": rule["lift"],
                    }

        addons = sorted(candidates.values(), key=lambda x: x["lift"], reverse=True)[:4]
        if not addons and self.rules:
            # Cold-start popular add-on when cart is empty or contains uncommon SKUs
            for rule in self.rules[:4]:
                c = rule["consequent_code"]
                if c not in item_set and not any(a["stock_code"] == c for a in addons):
                    addons.append({
                        "stock_code": c,
                        "description": rule["consequent_name"],
                        "unit_price": rule["consequent_price"],
                        "triggered_by": "POPULARITY",
                        "confidence_pct": rule["confidence_pct"],
                        "lift": rule["lift"],
                    })

        addon_value = round(sum(a["unit_price"] for a in addons[:2]), 2)
        combined_raw = round(base_subtotal + addon_value, 2)
        discounted_total = round(combined_raw * (1.0 - disc / 100.0), 2)
        cogs_est = round(combined_raw * 0.56, 2)
        net_margin_gbp = round(discounted_total - cogs_est, 2)
        aov_uplift_gbp = round(max(0.0, discounted_total - base_subtotal), 2)

        return {
            "status": "success",
            "cart_items": clean_items,
            "discount_pct": disc,
            "base_subtotal_gbp": base_subtotal,
            "recommended_bundle_total_gbp": discounted_total,
            "projected_aov_uplift_gbp": aov_uplift_gbp,
            "estimated_gross_margin_gbp": net_margin_gbp,
            "addons": addons,
        }


_BASKET_ENGINE_SINGLETON: Optional[MarketBasketEngine] = None


def get_basket_engine() -> MarketBasketEngine:
    """Returns process-wide singleton MarketBasketEngine instance."""
    global _BASKET_ENGINE_SINGLETON
    if _BASKET_ENGINE_SINGLETON is None:
        _BASKET_ENGINE_SINGLETON = MarketBasketEngine()
    return _BASKET_ENGINE_SINGLETON

