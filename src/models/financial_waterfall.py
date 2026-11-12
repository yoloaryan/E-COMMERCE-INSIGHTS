"""
Return & Refund Financial Waterfall + Geographic Net-Margin Analytics Engine (Phase 22).

Reconciles gross ordered GMV against empirical UCI return/cancellation leakage
(`IsCancelled` / negative quantity rows), COGS, and reverse-logistics costs:
1. 5-step Gross-to-Net P&L Contribution Margin Waterfall.
2. Country Unit Economics & Cancellation Leakage Matrix.
3. Top Return-Prone SKU Leakage Attribution & Root-Cause Tagging.
4. Interactive Return-Reduction EBITDA / Margin Recovery Simulator.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

DATA_PROCESSED_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"


def _build_synthetic_ledger(seed: int = 22) -> pd.DataFrame:
    """Deterministic multi-country positive + return ledger fallback for CI isolation."""
    rng = np.random.default_rng(seed)
    countries = [
        ("United Kingdom", 0.80, 0.042),
        ("Netherlands", 0.05, 0.018),
        ("EIRE", 0.05, 0.031),
        ("Germany", 0.04, 0.039),
        ("France", 0.03, 0.048),
        ("Spain", 0.03, 0.052),
    ]
    skus = [
        ("22423", "REGENCY CAKESTAND 3 TIER", 10.95),
        ("23843", "PAPER CRAFT , LITTLE BIRDIE", 2.08),
        ("47566", "PARTY BUNTING", 4.65),
        ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
        ("23166", "MEDIUM CERAMIC TOP STORAGE JAR", 1.04),
        ("22720", "SET OF 3 CAKE TINS PANTRY DESIGN", 4.95),
    ]

    rows: List[Dict[str, Any]] = []
    for country, share, cancel_p in countries:
        n_rows = int(round(1200 * share))
        for _ in range(n_rows):
            code, desc, price = skus[int(rng.integers(0, len(skus)))]
            is_cancel = rng.random() < cancel_p
            qty = int(rng.integers(4, 65))
            if is_cancel:
                qty = -qty
            amt = round(qty * price, 2)
            rows.append({
                "StockCode": code,
                "Description": desc,
                "Country": country,
                "Quantity": qty,
                "TotalPrice": amt,
                "IsCancelled": is_cancel,
            })
    return pd.DataFrame(rows)


class FinancialWaterfallEngine:
    """Computes P&L Waterfall, Geographic Margins, and Return Reduction Scenarios."""

    def __init__(self, use_parquet: bool = True):
        self.data_source: str = "synthetic_fallback"
        self.df: pd.DataFrame = self._load_ledger(use_parquet=use_parquet)
        self.available_countries: List[str] = self._compute_country_list()

    def _load_ledger(self, use_parquet: bool = True) -> pd.DataFrame:
        if use_parquet and DATA_PROCESSED_PATH.exists():
            try:
                raw = pd.read_parquet(
                    DATA_PROCESSED_PATH,
                    columns=["StockCode", "Description", "Country", "Quantity", "TotalPrice", "IsCancelled"],
                )
                raw = raw.copy()
                raw["StockCode"] = raw["StockCode"].astype(str).str.strip().str.upper()
                raw["Country"] = raw["Country"].astype(str).str.strip()
                raw["IsCancelled"] = raw["IsCancelled"].astype(bool) | (raw["Quantity"] < 0)
                self.data_source = "parquet_historical"
                return raw
            except Exception:
                pass

        self.data_source = "synthetic_fallback"
        return _build_synthetic_ledger()

    def _compute_country_list(self) -> List[str]:
        pos = self.df[~self.df["IsCancelled"]]
        top = pos.groupby("Country")["TotalPrice"].sum().sort_values(ascending=False).head(8).index.tolist()
        return ["All"] + [str(c) for c in top]

    def generate_waterfall_report(
        self,
        country: str = "All",
        cogs_ratio: float = 0.58,
    ) -> Dict[str, Any]:
        """Builds full P&L waterfall, Country unit economics, and high-return SKUs."""
        ratio = max(0.20, min(0.85, float(cogs_ratio)))
        selected_country = str(country or "All").strip()

        scoped = self.df
        if selected_country and selected_country.lower() != "all":
            filt = self.df[self.df["Country"].str.lower() == selected_country.lower()]
            if not filt.empty:
                scoped = filt

        pos = scoped[~scoped["IsCancelled"]]
        cancels = scoped[scoped["IsCancelled"]]

        gross_sales = round(float(pos["TotalPrice"].clip(lower=0.0).sum()), 2)
        return_leakage = round(float(cancels["TotalPrice"].abs().sum()), 2)
        net_revenue = round(gross_sales - return_leakage, 2)
        cogs_est = round(max(0.0, net_revenue) * ratio, 2)
        reverse_logistics = round(gross_sales * 0.06 + return_leakage * 0.12, 2)
        net_margin = round(net_revenue - cogs_est - reverse_logistics, 2)
        return_rate_pct = round((return_leakage / max(1.0, gross_sales)) * 100.0, 2)
        margin_pct = round((net_margin / max(1.0, net_revenue)) * 100.0, 1)

        waterfall = [
            {"step": "Gross Ordered GMV", "amount_gbp": gross_sales, "type": "positive"},
            {"step": "Returns & Cancellations", "amount_gbp": round(-return_leakage, 2), "type": "negative"},
            {"step": "Net Realized Revenue", "amount_gbp": net_revenue, "type": "subtotal"},
            {"step": "COGS & Reverse Logistics", "amount_gbp": round(-(cogs_est + reverse_logistics), 2), "type": "negative"},
            {"step": "Net Contribution Margin", "amount_gbp": net_margin, "type": "total"},
        ]

        # Country unit economics across full dataset
        country_grp_pos = self.df[~self.df["IsCancelled"]].groupby("Country")["TotalPrice"].sum()
        country_grp_ret = self.df[self.df["IsCancelled"]].groupby("Country")["TotalPrice"].apply(lambda s: s.abs().sum())
        all_c = sorted(
            set(country_grp_pos.nlargest(8).index.tolist()),
            key=lambda c: float(country_grp_pos.get(c, 0.0)),
            reverse=True,
        )
        country_margins: List[Dict[str, Any]] = []
        for c_name in all_c:
            gmv = round(float(country_grp_pos.get(c_name, 0.0)), 2)
            ret = round(float(country_grp_ret.get(c_name, 0.0)), 2)
            net_r = round(gmv - ret, 2)
            m_gbp = round(net_r * (1.0 - ratio) - gmv * 0.06 - ret * 0.12, 2)
            country_margins.append({
                "country": c_name,
                "gross_gmv_gbp": gmv,
                "return_leakage_gbp": ret,
                "return_rate_pct": round((ret / max(1.0, gmv)) * 100.0, 2),
                "net_revenue_gbp": net_r,
                "net_margin_gbp": m_gbp,
            })

        # Top return-prone SKUs in scoped slice
        sku_pos = pos.groupby("StockCode").agg(desc=("Description", "first"), gmv=("TotalPrice", "sum"))
        sku_ret = cancels.groupby("StockCode").agg(
            desc=("Description", "first"),
            refund_gbp=("TotalPrice", lambda s: float(s.abs().sum())),
            cancel_lines=("TotalPrice", "count"),
        )
        high_return_skus: List[Dict[str, Any]] = []
        if not sku_ret.empty:
            top_ret = sku_ret.sort_values("refund_gbp", ascending=False).head(6)
            for code, row in top_ret.iterrows():
                ref = round(float(row["refund_gbp"]), 2)
                gmv_val = float(sku_pos.loc[code, "gmv"]) if code in sku_pos.index else ref
                r_rate = round(min(100.0, (ref / max(1.0, gmv_val + ref)) * 100.0), 1)
                cause = "Bulk Wholesale Reversal" if ref > 5000 else ("Fragile / Transit Breakage" if r_rate > 12 else "Order Modification / Sizing")
                high_return_skus.append({
                    "stock_code": str(code),
                    "description": str(row["desc"] or f"SKU {code}").strip()[:48].title(),
                    "refund_leakage_gbp": ref,
                    "cancel_events": int(row["cancel_lines"]),
                    "return_rate_pct": r_rate,
                    "root_cause_driver": cause,
                })

        return {
            "status": "healthy",
            "data_source": self.data_source,
            "filters": {"country": selected_country, "cogs_ratio": ratio},
            "available_countries": self.available_countries,
            "summary": {
                "gross_gmv_gbp": gross_sales,
                "return_leakage_gbp": return_leakage,
                "net_revenue_gbp": net_revenue,
                "cogs_estimate_gbp": cogs_est,
                "reverse_logistics_gbp": reverse_logistics,
                "net_contribution_margin_gbp": net_margin,
                "return_rate_pct": return_rate_pct,
                "contribution_margin_pct": margin_pct,
            },
            "waterfall": waterfall,
            "country_margins": country_margins,
            "high_return_skus": high_return_skus,
        }

    def simulate_margin_recovery(
        self,
        return_reduction_pct: float = 25.0,
        country: str = "All",
        cogs_ratio: float = 0.58,
    ) -> Dict[str, Any]:
        """Simulates EBITDA/margin recovered by reducing product return/cancellation leakage."""
        red = max(0.0, min(75.0, float(return_reduction_pct)))
        base = self.generate_waterfall_report(country=country, cogs_ratio=cogs_ratio)
        s = base["summary"]

        saved_revenue = round(s["return_leakage_gbp"] * (red / 100.0), 2)
        avoided_rev_logistics = round(saved_revenue * 0.12, 2)
        incremental_margin = round(saved_revenue * (1.0 - float(cogs_ratio)) + avoided_rev_logistics, 2)
        new_return_rate = round(s["return_rate_pct"] * (1.0 - red / 100.0), 2)

        return {
            "status": "success",
            "inputs": {"return_reduction_pct": red, "country": country, "cogs_ratio": cogs_ratio},
            "outputs": {
                "baseline_return_rate_pct": s["return_rate_pct"],
                "target_return_rate_pct": new_return_rate,
                "recovered_top_line_gbp": saved_revenue,
                "avoided_reverse_logistics_gbp": avoided_rev_logistics,
                "incremental_net_margin_gbp": incremental_margin,
                "projected_total_margin_gbp": round(s["net_contribution_margin_gbp"] + incremental_margin, 2),
            },
        }


_WATERFALL_SINGLETON: Optional[FinancialWaterfallEngine] = None


def get_waterfall_engine() -> FinancialWaterfallEngine:
    """Returns process-wide singleton FinancialWaterfallEngine instance."""
    global _WATERFALL_SINGLETON
    if _WATERFALL_SINGLETON is None:
        _WATERFALL_SINGLETON = FinancialWaterfallEngine()
    return _WATERFALL_SINGLETON
