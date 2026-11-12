"""
Cohort Retention Heatmap & RFM Segment Migration Intelligence Engine (Phase 18).

Provides longitudinal customer lifecycle analytics:
1. Monthly Acquisition Cohort Retention Matrix (M0..M12): tracks both
   logo (unique buyer) repeat retention % and Net Revenue Retention (NRR %).
2. RFM Markov Segment Migration Matrix: splits transactions across Prior vs. Current
   windows and tracks segment retention, slippage (Champions -> At-Risk), and
   win-back migrations (Hibernating/At-Risk -> Loyal/Champions).
3. Interactive Retention Lift Simulator: projects annualized LTV yield from improving
   Month-1 onboarding repeat rate and winning back lapsed high-value accounts.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

DATA_PROCESSED_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"

SEGMENT_ORDER = ["Champions", "Loyal", "At-Risk", "Hibernating"]


def _build_synthetic_transactions(seed: int = 18) -> pd.DataFrame:
    """
    Deterministic longitudinal fallback transactions spanning 13 months
    used when processed Parquet data is absent (e.g., isolated CI).
    """
    rng = np.random.default_rng(seed)
    months = pd.period_range("2010-12", periods=13, freq="M")
    countries = ["United Kingdom", "Germany", "France", "EIRE", "Netherlands", "Spain"]

    rows: List[Dict[str, Any]] = []
    cid_counter = 12000

    for m_idx, acq_period in enumerate(months):
        n_acq = int(160 + (m_idx % 4) * 28 + (40 if acq_period.month in (11, 12) else 0))
        for _ in range(n_acq):
            cid_counter += 1
            cid = str(cid_counter)
            country = str(rng.choice(countries, p=[0.82, 0.05, 0.05, 0.03, 0.03, 0.02]))
            base_spend = float(round(rng.lognormal(mean=5.1, sigma=0.75), 2))
            # Month 0 purchase
            rows.append({
                "CustomerID": cid,
                "InvoicePeriod": acq_period,
                "Country": country,
                "Amount": base_spend,
            })

            # Simulate repeat purchases across subsequent months
            stickiness = 0.42 if base_spend > 260 else 0.24
            for offset in range(1, len(months) - m_idx):
                decay_prob = max(0.06, stickiness * (0.86 ** (offset - 1)))
                if rng.random() < decay_prob:
                    repeat_amt = float(round(base_spend * rng.uniform(0.65, 1.35), 2))
                    rows.append({
                        "CustomerID": cid,
                        "InvoicePeriod": acq_period + offset,
                        "Country": country,
                        "Amount": repeat_amt,
                    })

    return pd.DataFrame(rows)


def _assign_rfm_tier(freq: int, monetary: float, is_active_recent: bool) -> str:
    """Deterministic tier classifier aligned with RFM Champions/Loyal/At-Risk/Hibernating."""
    if is_active_recent and (freq >= 4 or monetary >= 1800.0):
        return "Champions"
    if is_active_recent:
        return "Loyal"
    if freq >= 2 or monetary >= 600.0:
        return "At-Risk"
    return "Hibernating"


class CohortAnalyticsEngine:
    """Pre-aggregated longitudinal Cohort Retention & Segment Migration Engine."""

    def __init__(self, use_parquet: bool = True):
        self.data_source: str = "synthetic_fallback"
        self.df: pd.DataFrame = self._load_transactions(use_parquet=use_parquet)
        self.available_countries: List[str] = self._compute_country_options()

    def _load_transactions(self, use_parquet: bool = True) -> pd.DataFrame:
        if use_parquet and DATA_PROCESSED_PATH.exists():
            try:
                raw = pd.read_parquet(
                    DATA_PROCESSED_PATH,
                    columns=["CustomerID", "InvoiceDate", "Quantity", "UnitPrice", "Country"],
                )
                raw = raw.dropna(subset=["CustomerID"]).copy()
                raw["CustomerID"] = raw["CustomerID"].astype(str).str.strip()
                raw = raw[(raw["CustomerID"] != "") & (raw["CustomerID"].str.lower() != "none")]
                raw = raw[(raw["Quantity"] > 0) & (raw["UnitPrice"] > 0)].copy()
                raw["Amount"] = (raw["Quantity"] * raw["UnitPrice"]).astype(float)
                raw["InvoicePeriod"] = pd.to_datetime(raw["InvoiceDate"]).dt.to_period("M")
                agg = raw.groupby(["CustomerID", "InvoicePeriod", "Country"], as_index=False)["Amount"].sum()
                self.data_source = "parquet_historical"
                return agg
            except Exception:
                pass

        self.data_source = "synthetic_fallback"
        return _build_synthetic_transactions()

    def _compute_country_options(self) -> List[str]:
        top = (
            self.df.groupby("Country")["Amount"]
            .sum()
            .sort_values(ascending=False)
            .head(8)
            .index.tolist()
        )
        return ["All"] + [str(c) for c in top]

    def generate_retention_report(
        self,
        metric: str = "customers",
        country: str = "All",
    ) -> Dict[str, Any]:
        """
        Builds M0..M12 Monthly Acquisition Cohort matrix for customer retention (%)
        or Net Revenue Retention (%).
        """
        df_scoped = self.df
        selected_country = str(country or "All").strip()
        if selected_country and selected_country.lower() != "all":
            filtered = self.df[self.df["Country"].str.lower() == selected_country.lower()]
            if not filtered.empty:
                df_scoped = filtered

        first_period = df_scoped.groupby("CustomerID")["InvoicePeriod"].transform("min")
        work = df_scoped.assign(CohortMonth=first_period)
        work["CohortIndex"] = (work["InvoicePeriod"].astype("int64") - work["CohortMonth"].astype("int64"))
        work = work[work["CohortIndex"] >= 0]

        cohort_groups = (
            work.groupby(["CohortMonth", "CohortIndex"])
            .agg(
                active_customers=("CustomerID", "nunique"),
                revenue_gbp=("Amount", "sum"),
            )
            .reset_index()
        )

        all_cohorts = sorted(work["CohortMonth"].unique())
        max_index = int(min(12, max(0, cohort_groups["CohortIndex"].max()))) if not cohort_groups.empty else 0

        cust_piv = cohort_groups.pivot(index="CohortMonth", columns="CohortIndex", values="active_customers")
        rev_piv = cohort_groups.pivot(index="CohortMonth", columns="CohortIndex", values="revenue_gbp")

        rows: List[Dict[str, Any]] = []
        col_buckets: Dict[int, List[float]] = {idx: [] for idx in range(max_index + 1)}
        nrr_buckets: Dict[int, List[float]] = {idx: [] for idx in range(max_index + 1)}

        for c_period in all_cohorts:
            base_cust = float(cust_piv.loc[c_period, 0]) if 0 in cust_piv.columns and pd.notna(cust_piv.loc[c_period, 0]) else 0.0
            base_rev = float(rev_piv.loc[c_period, 0]) if 0 in rev_piv.columns and pd.notna(rev_piv.loc[c_period, 0]) else 0.0
            if base_cust <= 0:
                continue

            cust_pcts: List[Optional[float]] = []
            rev_pcts: List[Optional[float]] = []
            raw_counts: List[Optional[int]] = []

            for idx in range(max_index + 1):
                c_val = cust_piv.loc[c_period, idx] if idx in cust_piv.columns else np.nan
                r_val = rev_piv.loc[c_period, idx] if idx in rev_piv.columns else np.nan
                # Future months beyond latest observed invoice month stay None
                if c_period + idx > all_cohorts[-1]:
                    cust_pcts.append(None)
                    rev_pcts.append(None)
                    raw_counts.append(None)
                else:
                    cnt = int(c_val) if pd.notna(c_val) else 0
                    rev = float(r_val) if pd.notna(r_val) else 0.0
                    c_pct = round((cnt / base_cust) * 100.0, 1)
                    r_pct = round((rev / max(1.0, base_rev)) * 100.0, 1)
                    cust_pcts.append(c_pct)
                    rev_pcts.append(r_pct)
                    raw_counts.append(cnt)
                    col_buckets[idx].append(c_pct)
                    nrr_buckets[idx].append(r_pct)

            rows.append({
                "cohort_month": str(c_period),
                "cohort_size": int(base_cust),
                "month0_revenue_gbp": round(base_rev, 2),
                "customer_retention_pcts": cust_pcts,
                "revenue_retention_pcts": rev_pcts,
                "active_counts": raw_counts,
            })

        avg_customer_curve = [
            round(float(np.mean(col_buckets[idx])), 1) if col_buckets[idx] else None
            for idx in range(max_index + 1)
        ]
        avg_revenue_curve = [
            round(float(np.mean(nrr_buckets[idx])), 1) if nrr_buckets[idx] else None
            for idx in range(max_index + 1)
        ]

        # Best acquisition cohort by Month 1 (excluding latest month that lacks Month 1)
        mature_rows = [r for r in rows if len(r["customer_retention_pcts"]) > 1 and r["customer_retention_pcts"][1] is not None]
        best_cohort = max(mature_rows, key=lambda r: float(r["customer_retention_pcts"][1] or 0.0))["cohort_month"] if mature_rows else (rows[0]["cohort_month"] if rows else "N/A")

        m1_avg = avg_customer_curve[1] if len(avg_customer_curve) > 1 and avg_customer_curve[1] is not None else 0.0
        m3_avg = avg_customer_curve[3] if len(avg_customer_curve) > 3 and avg_customer_curve[3] is not None else m1_avg
        m6_avg = avg_customer_curve[6] if len(avg_customer_curve) > 6 and avg_customer_curve[6] is not None else m3_avg
        nrr_m1_avg = avg_revenue_curve[1] if len(avg_revenue_curve) > 1 and avg_revenue_curve[1] is not None else 0.0

        return {
            "status": "success",
            "data_source": self.data_source,
            "metric": "revenue" if str(metric).lower() == "revenue" else "customers",
            "country": selected_country,
            "available_countries": self.available_countries,
            "max_month_index": max_index,
            "month_headers": [f"M{i}" for i in range(max_index + 1)],
            "summary": {
                "total_cohorts": len(rows),
                "total_tracked_customers": sum(r["cohort_size"] for r in rows),
                "avg_month1_retention_pct": m1_avg,
                "avg_month3_retention_pct": m3_avg,
                "avg_month6_retention_pct": m6_avg,
                "avg_month1_nrr_pct": nrr_m1_avg,
                "best_cohort_month": best_cohort,
            },
            "average_curve": {
                "labels": [f"Month {i}" for i in range(max_index + 1)],
                "customer_retention_pct": avg_customer_curve,
                "revenue_retention_pct": avg_revenue_curve,
            },
            "cohorts": rows,
        }

    def generate_migration_report(self) -> Dict[str, Any]:
        """
        Computes Prior Window (early half) -> Current Window (recent half)
        RFM 4x4 Markov Transition Matrix across all observed repeat-window accounts.
        """
        periods = sorted(self.df["InvoicePeriod"].unique())
        split_idx = max(1, len(periods) // 2)
        prior_cutoff = periods[split_idx - 1]
        prior_recent_floor = periods[max(0, split_idx - 3)]
        current_recent_floor = periods[max(split_idx, len(periods) - 3)]

        prior_df = self.df[self.df["InvoicePeriod"] <= prior_cutoff]
        curr_df = self.df[self.df["InvoicePeriod"] > prior_cutoff]

        prior_stats = (
            prior_df.groupby("CustomerID")
            .agg(
                freq=("InvoicePeriod", "count"),
                monetary=("Amount", "sum"),
                last_period=("InvoicePeriod", "max"),
            )
            .to_dict("index")
        )
        curr_stats = (
            curr_df.groupby("CustomerID")
            .agg(
                freq=("InvoicePeriod", "count"),
                monetary=("Amount", "sum"),
                last_period=("InvoicePeriod", "max"),
            )
            .to_dict("index")
        )

        counts: Dict[str, Dict[str, int]] = {
            src: {dst: 0 for dst in SEGMENT_ORDER} for src in SEGMENT_ORDER
        }
        rev_flows: Dict[str, Dict[str, float]] = {
            src: {dst: 0.0 for dst in SEGMENT_ORDER} for src in SEGMENT_ORDER
        }

        tracked_accounts = 0
        champions_retained = 0
        champions_slipped = 0
        champions_slipped_rev = 0.0
        winback_upgrades = 0
        winback_rev = 0.0

        for cid, p_meta in prior_stats.items():
            tracked_accounts += 1
            src_seg = _assign_rfm_tier(
                int(p_meta["freq"]),
                float(p_meta["monetary"]),
                p_meta["last_period"] >= prior_recent_floor,
            )

            c_meta = curr_stats.get(cid)
            if c_meta is None:
                # Account made zero purchases in the Current Window -> migrated down
                dst_seg = "At-Risk" if src_seg in ("Champions", "Loyal") else "Hibernating"
                rev_impact = float(p_meta["monetary"])
            else:
                dst_seg = _assign_rfm_tier(
                    int(p_meta["freq"] + c_meta["freq"]),
                    float(p_meta["monetary"] + c_meta["monetary"]),
                    c_meta["last_period"] >= current_recent_floor,
                )
                rev_impact = float(c_meta["monetary"])

            counts[src_seg][dst_seg] += 1
            rev_flows[src_seg][dst_seg] += rev_impact

            if src_seg == "Champions":
                if dst_seg == "Champions":
                    champions_retained += 1
                elif dst_seg in ("At-Risk", "Hibernating"):
                    champions_slipped += 1
                    champions_slipped_rev += float(p_meta["monetary"])
            elif src_seg in ("At-Risk", "Hibernating") and dst_seg in ("Champions", "Loyal"):
                winback_upgrades += 1
                winback_rev += rev_impact

        matrix_rows: List[Dict[str, Any]] = []
        for src in SEGMENT_ORDER:
            row_total = sum(counts[src].values())
            transitions: Dict[str, Dict[str, Any]] = {}
            for dst in SEGMENT_ORDER:
                cnt = counts[src][dst]
                pct = round((cnt / row_total) * 100.0, 1) if row_total > 0 else 0.0
                transitions[dst] = {
                    "count": cnt,
                    "pct": pct,
                    "revenue_gbp": round(rev_flows[src][dst], 2),
                }
            matrix_rows.append({
                "from_segment": src,
                "total_accounts": row_total,
                "transitions": transitions,
            })

        total_prior_champions = max(1, sum(counts["Champions"].values()))
        champion_stay_rate_pct = round((champions_retained / total_prior_champions) * 100.0, 1)

        return {
            "status": "success",
            "data_source": self.data_source,
            "window_split": {
                "prior_through": str(prior_cutoff),
                "current_from": str(periods[min(split_idx, len(periods) - 1)]),
            },
            "segments": SEGMENT_ORDER,
            "summary": {
                "tracked_prior_accounts": tracked_accounts,
                "champion_stay_rate_pct": champion_stay_rate_pct,
                "champions_slipped_count": champions_slipped,
                "champions_slipped_revenue_gbp": round(champions_slipped_rev, 2),
                "winback_upgrades_count": winback_upgrades,
                "winback_recovered_revenue_gbp": round(winback_rev, 2),
            },
            "matrix": matrix_rows,
        }

    def simulate_retention_lift(
        self,
        month1_lift_pp: float = 5.0,
        winback_recovery_pct: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Projects incremental annualized LTV yield from lifting Month-1 repeat conversion
        and reactivating slipped Champions / At-Risk accounts.
        """
        lift_pp = max(0.0, min(35.0, float(month1_lift_pp)))
        winback_pct = max(0.0, min(60.0, float(winback_recovery_pct)))

        ret = self.generate_retention_report(metric="customers")
        mig = self.generate_migration_report()

        total_cust = max(1, ret["summary"]["total_tracked_customers"])
        avg_order_value = float(self.df["Amount"].mean()) if not self.df.empty else 320.0
        extra_repeat_buyers = int(round(total_cust * (lift_pp / 100.0)))
        # Expect 2.2 follow-on purchases over 12 months for rescued Month-1 repeaters
        repeat_ltv_gain = round(extra_repeat_buyers * avg_order_value * 2.2, 2)

        slipped_cnt = mig["summary"]["champions_slipped_count"]
        slipped_rev = mig["summary"]["champions_slipped_revenue_gbp"]
        recovered_accounts = int(round(slipped_cnt * (winback_pct / 100.0)))
        winback_ltv_gain = round(slipped_rev * (winback_pct / 100.0) * 0.65, 2)

        total_projected_gain = round(repeat_ltv_gain + winback_ltv_gain, 2)
        baseline_m1 = ret["summary"]["avg_month1_retention_pct"]
        projected_m1 = round(min(98.0, baseline_m1 + lift_pp), 1)

        return {
            "status": "success",
            "inputs": {
                "month1_lift_pp": lift_pp,
                "winback_recovery_pct": winback_pct,
            },
            "outputs": {
                "baseline_month1_retention_pct": baseline_m1,
                "projected_month1_retention_pct": projected_m1,
                "incremental_repeat_buyers": extra_repeat_buyers,
                "recovered_slipping_accounts": recovered_accounts,
                "repeat_lift_revenue_gbp": repeat_ltv_gain,
                "winback_recovery_revenue_gbp": winback_ltv_gain,
                "total_annual_revenue_lift_gbp": total_projected_gain,
            },
        }


_COHORT_ENGINE_SINGLETON: Optional[CohortAnalyticsEngine] = None


def get_cohort_engine() -> CohortAnalyticsEngine:
    """Returns process-wide singleton CohortAnalyticsEngine instance."""
    global _COHORT_ENGINE_SINGLETON
    if _COHORT_ENGINE_SINGLETON is None:
        _COHORT_ENGINE_SINGLETON = CohortAnalyticsEngine()
    return _COHORT_ENGINE_SINGLETON
