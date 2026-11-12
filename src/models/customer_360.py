"""
Unified Customer-360 Intelligence & Ledger Engine (Phase 24).

Aggregates longitudinal transaction history across all registered retail accounts:
1. Financial profile: Gross Spend, Return/Refund Leakage, Net Realized Spend & Return Rate %.
2. Behavioral RFM metrics: Order Count, AOV, Recency Days, Tenure Days & Segment Classification.
3. Risk & Action Engine: Heuristic Churn Probability, Top Purchased SKUs & Next-Best-Action Strategy.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

DATA_PROCESSED_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"


def _classify_segment(spend: float, orders: int, recency: int) -> str:
    if recency <= 45 and (orders >= 8 or spend >= 3500.0):
        return "Champions (VIP)"
    if recency <= 60:
        return "Loyal Customers"
    if spend >= 1200.0 or orders >= 5:
        return "At-Risk / Lapsing"
    return "Occasional / Hibernating"


def _compute_churn_prob(recency: int, orders: int, return_rate_pct: float) -> float:
    base = 0.06 + (min(365, max(0, recency)) / 240.0) * 0.68
    freq_bonus = min(0.24, (orders / 25.0) * 0.16)
    return_penalty = min(0.14, (return_rate_pct / 100.0) * 0.25)
    return round(max(0.02, min(0.96, base - freq_bonus + return_penalty)), 3)


def _recommend_next_action(segment: str, return_rate_pct: float, churn_prob: float) -> str:
    if return_rate_pct >= 15.0:
        return "Quality Assurance Check-in + Sizing Guide Concierge"
    if segment == "At-Risk / Lapsing" or churn_prob >= 0.65:
        return "Executive VIP Win-Back Outreach + 20% Reactivation Voucher"
    if segment == "Champions (VIP)":
        return "Early Access Preview + Priority Allocation Tier"
    if segment == "Loyal Customers":
        return "High-Lift Complementary Bundle Cross-Sell"
    return "Re-Engagement Discovery Campaign"


def _build_synthetic_profiles(seed: int = 24) -> Dict[str, Dict[str, Any]]:
    rng = np.random.default_rng(seed)
    known = [
        ("14646", "Netherlands", 280206.02, 74, 1, ["Regency Cakestand 3 Tier", "Paper Craft Birdie", "Jumbo Bag Red Retrospot"]),
        ("18102", "United Kingdom", 259657.30, 60, 1, ["Vintage Union Jack Bunting", "Party Bunting", "Paper Chain Kit"]),
        ("17850", "United Kingdom", 5391.21, 35, 2, ["White Hanging Heart T-Light Holder", "Regency Cakestand", "Red T-Light Holder"]),
        ("14096", "United Kingdom", 65164.79, 17, 84, ["Party Bunting", "Wholesale Gift Lot", "Retrospot Lunch Bag"]),
        ("12352", "Norway", 2506.04, 8, 72, ["Ceramic Cake Tins", "Regency Teacup", "Gift Boxes"]),
        ("15311", "United Kingdom", 1980.45, 11, 14, ["Green Regency Teacup", "Cake Tins", "Lunch Bag Red Retrospot"]),
        ("13089", "United Kingdom", 58825.34, 118, 3, ["Jumbo Storage Bags", "Christmas Craft Kit", "Bird Ornament"]),
        ("15838", "United Kingdom", 336.14, 1, 210, ["Hanging Heart Decoration"]),
    ]
    profiles: Dict[str, Dict[str, Any]] = {}
    for cid, ctry, spend, orders, rec, hist in known:
        ret = round(float(rng.uniform(0.0, spend * 0.05)), 2)
        net = round(spend - ret, 2)
        rr = round((ret / max(1.0, spend)) * 100.0, 2)
        seg = _classify_segment(spend, orders, rec)
        cprob = _compute_churn_prob(rec, orders, rr)
        profiles[cid] = {
            "id": cid,
            "customer_id": cid,
            "country": ctry,
            "spend": net,
            "gross_spend_gbp": round(spend, 2),
            "refund_amount_gbp": ret,
            "net_spend_gbp": net,
            "return_rate_pct": rr,
            "orders": orders,
            "distinct_skus": max(2, orders * 3),
            "aov": round(net / max(1, orders), 2),
            "recency": rec,
            "tenure_days": rec + orders * 7,
            "segment": seg,
            "churnProb": cprob,
            "next_best_action": _recommend_next_action(seg, rr, cprob),
            "history": hist,
        }

    for idx in range(12):
        cid = str(16100 + idx)
        spend = round(float(rng.uniform(450, 9500)), 2)
        orders = int(rng.integers(2, 22))
        rec = int(rng.integers(3, 180))
        ret = round(spend * float(rng.uniform(0.0, 0.08)), 2)
        net = round(spend - ret, 2)
        rr = round((ret / max(1.0, spend)) * 100.0, 2)
        seg = _classify_segment(spend, orders, rec)
        cprob = _compute_churn_prob(rec, orders, rr)
        profiles[cid] = {
            "id": cid,
            "customer_id": cid,
            "country": "United Kingdom",
            "spend": net,
            "gross_spend_gbp": spend,
            "refund_amount_gbp": ret,
            "net_spend_gbp": net,
            "return_rate_pct": rr,
            "orders": orders,
            "distinct_skus": max(2, orders * 2),
            "aov": round(net / max(1, orders), 2),
            "recency": rec,
            "tenure_days": rec + orders * 9,
            "segment": seg,
            "churnProb": cprob,
            "next_best_action": _recommend_next_action(seg, rr, cprob),
            "history": ["Regency Cakestand 3 Tier", "Lunch Bag Red Retrospot"],
        }
    return profiles


class Customer360Engine:
    """In-memory Customer-360 intelligence index backing ledger search & drawers."""

    def __init__(self, use_parquet: bool = True):
        self.data_source: str = "synthetic_fallback"
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.sorted_ids: List[str] = []
        self._load_profiles(use_parquet=use_parquet)

    def _load_profiles(self, use_parquet: bool = True) -> None:
        if use_parquet and DATA_PROCESSED_PATH.exists():
            try:
                raw = pd.read_parquet(
                    DATA_PROCESSED_PATH,
                    columns=[
                        "CustomerID", "InvoiceNo", "StockCode", "Description",
                        "Quantity", "TotalPrice", "Country", "InvoiceDate", "IsCancelled",
                    ],
                )
                raw = raw.dropna(subset=["CustomerID"]).copy()
                raw["CustomerID"] = raw["CustomerID"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
                raw = raw[(raw["CustomerID"] != "") & (raw["CustomerID"].str.lower() != "none")]
                raw["InvoiceDate"] = pd.to_datetime(raw["InvoiceDate"])
                raw["IsCancelled"] = raw["IsCancelled"].astype(bool) | (raw["Quantity"] < 0)

                max_date = raw["InvoiceDate"].max()
                pos = raw[~raw["IsCancelled"]]
                neg = raw[raw["IsCancelled"]]

                pos_agg = pos.groupby("CustomerID").agg(
                    gross_spend=("TotalPrice", "sum"),
                    orders=("InvoiceNo", "nunique"),
                    distinct_skus=("StockCode", "nunique"),
                    first_date=("InvoiceDate", "min"),
                    last_date=("InvoiceDate", "max"),
                    country=("Country", "first"),
                )
                neg_agg = neg.groupby("CustomerID")["TotalPrice"].apply(lambda s: float(s.abs().sum()))

                # Top 3 SKU descriptions per customer using sorted value counts
                top_items_df = (
                    pos.groupby(["CustomerID", "Description"])["TotalPrice"]
                    .sum()
                    .reset_index()
                    .sort_values(["CustomerID", "TotalPrice"], ascending=[True, False])
                )
                hist_map: Dict[str, List[str]] = {}
                for cid, grp in top_items_df.groupby("CustomerID", sort=False):
                    hist_map[str(cid)] = [str(d).strip().title()[:45] for d in grp["Description"].head(3).tolist()]

                for cid, row in pos_agg.iterrows():
                    cid_s = str(cid)
                    gross = round(max(0.0, float(row["gross_spend"])), 2)
                    refund = round(float(neg_agg.get(cid, 0.0)), 2)
                    net = round(max(0.0, gross - refund), 2)
                    rr = round(min(100.0, (refund / max(1.0, gross)) * 100.0), 2)
                    orders = max(1, int(row["orders"]))
                    recency = max(0, int((max_date - row["last_date"]).days))
                    tenure = max(recency + 1, int((max_date - row["first_date"]).days))
                    seg = _classify_segment(net, orders, recency)
                    cprob = _compute_churn_prob(recency, orders, rr)
                    self.profiles[cid_s] = {
                        "id": cid_s,
                        "customer_id": cid_s,
                        "country": str(row["country"] or "United Kingdom"),
                        "spend": net,
                        "gross_spend_gbp": gross,
                        "refund_amount_gbp": refund,
                        "net_spend_gbp": net,
                        "return_rate_pct": rr,
                        "orders": orders,
                        "distinct_skus": int(row["distinct_skus"]),
                        "aov": round(net / orders, 2),
                        "recency": recency,
                        "tenure_days": tenure,
                        "segment": seg,
                        "churnProb": cprob,
                        "next_best_action": _recommend_next_action(seg, rr, cprob),
                        "history": hist_map.get(cid_s, ["Retail Merchandising Basket"]),
                    }

                self.sorted_ids = sorted(
                    self.profiles.keys(),
                    key=lambda c: self.profiles[c]["net_spend_gbp"],
                    reverse=True,
                )
                self.data_source = "parquet_historical"
                return
            except Exception:
                pass

        self.profiles = _build_synthetic_profiles()
        self.sorted_ids = sorted(
            self.profiles.keys(),
            key=lambda c: self.profiles[c]["net_spend_gbp"],
            reverse=True,
        )
        self.data_source = "synthetic_fallback"

    def query_ledger(
        self,
        segment: str = "all",
        search: str = "",
        limit: int = 40,
    ) -> Dict[str, Any]:
        """Filters and returns paginated Customer-360 ledger records."""
        seg_filter = str(segment or "all").strip()
        q = str(search or "").strip().lower()
        lim = max(1, min(200, int(limit)))

        matches: List[Dict[str, Any]] = []
        total_matching = 0
        for cid in self.sorted_ids:
            rec = self.profiles[cid]
            if seg_filter != "all" and rec["segment"].lower() != seg_filter.lower():
                continue
            if q and q not in cid.lower() and q not in rec["country"].lower():
                continue
            total_matching += 1
            if len(matches) < lim:
                matches.append(rec)

        return {
            "status": "success",
            "data_source": self.data_source,
            "total_catalog_customers": len(self.profiles),
            "total_matching": total_matching,
            "customers": matches,
        }

    def get_customer_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        clean = str(customer_id or "").strip()
        return self.profiles.get(clean)


_CUSTOMER_360_SINGLETON: Optional[Customer360Engine] = None


def get_customer_360_engine() -> Customer360Engine:
    """Returns process-wide singleton Customer360Engine instance."""
    global _CUSTOMER_360_SINGLETON
    if _CUSTOMER_360_SINGLETON is None:
        _CUSTOMER_360_SINGLETON = Customer360Engine()
    return _CUSTOMER_360_SINGLETON

