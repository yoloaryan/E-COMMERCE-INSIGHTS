"""
Advanced Probabilistic Customer Lifetime Value (CLV) Engine using BTYD Models.

Implements:
1. BG/NBD (Beta-Geometric / Negative Binomial Distribution) for transaction rate (lambda)
   and dropout probability (p) estimation in non-contractual e-commerce.
2. Gamma-Gamma Submodel for conditional expected monetary order values.
3. 12-Month Discounted Customer Lifetime Value (CLV) projections.
4. Continuous P(Alive) scoring without arbitrary inactivity cutoffs.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import numpy as np
import pandas as pd
import joblib
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data

DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"
CUSTOMER_CENTRIC_PQ = DATA_PROCESSED_DIR / "online_retail_customer_centric.parquet"
CUSTOMER_CENTRIC_CSV = DATA_PROCESSED_DIR / "online_retail_customer_centric.csv"


class BTYDCustomerLifetimeValue:
    """
    Probabilistic BTYD Modeling Engine:
    - Eliminates arbitrary churn thresholds (e.g. 90-day cutoffs).
    - Models underlying purchase latency and dropout hazard rates.
    - Estimates future monetary contributions discounted to Net Present Value.
    """

    def __init__(self, data_path: Path = None, penalizer_coef: float = 0.05):
        if data_path is None:
            data_path = CUSTOMER_CENTRIC_PQ if CUSTOMER_CENTRIC_PQ.exists() else CUSTOMER_CENTRIC_CSV
        self.data_path = data_path
        self.penalizer_coef = penalizer_coef
        self.df_raw: pd.DataFrame = None
        self.rfm_summary: pd.DataFrame = None
        self.bgf: BetaGeoFitter = None
        self.ggf: GammaGammaFitter = None
        self.clv_predictions: pd.DataFrame = None

    def load_and_prepare_rfm(self) -> pd.DataFrame:
        """
        Transforms transactional logs into RFM summary format required by BTYD:
        - frequency: number of repeat transaction weeks
        - recency: time in weeks between first and last transaction
        - T: total customer age/tenure in weeks from first transaction to observation end
        - monetary_value: average value of repeat purchases
        """
        print(f"[BTYD] Loading transactional dataset from {self.data_path}...")
        if str(self.data_path).endswith(".parquet"):
            df = pd.read_parquet(self.data_path)
        else:
            df = pd.read_csv(self.data_path, parse_dates=["InvoiceDate"])

        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
        df["CustomerID"] = df["CustomerID"].astype(str)
        self.df_raw = df

        max_date = df["InvoiceDate"].max()
        print(f"[BTYD] Calculating Weekly RFM summary (Observation End Date: {max_date.date()})...")

        rfm = summary_data_from_transaction_data(
            df,
            customer_id_col="CustomerID",
            datetime_col="InvoiceDate",
            monetary_value_col="TotalPrice",
            observation_period_end=max_date,
            freq="W"
        )

        # Filter customers with monetary value >= 0
        rfm = rfm[rfm["monetary_value"] >= 0].copy()
        self.rfm_summary = rfm
        print(f"[BTYD] Weekly RFM Summary generated for {len(rfm):,} unique customers.")
        return self.rfm_summary

    def fit_bg_nbd_model(self) -> BetaGeoFitter:
        """
        Fits BG/NBD model using Maximum Likelihood Estimation.
        Estimates parameters r, alpha (transaction rate distribution)
        and a, b (dropout probability distribution).
        """
        if self.rfm_summary is None:
            self.load_and_prepare_rfm()

        print("[BTYD] Fitting BG/NBD Model (Transaction & Dropout Process)...")
        self.bgf = BetaGeoFitter(penalizer_coef=self.penalizer_coef)
        self.bgf.fit(
            self.rfm_summary["frequency"],
            self.rfm_summary["recency"],
            self.rfm_summary["T"]
        )

        params = self.bgf.summary
        print(f"[BTYD] BG/NBD Parameters: r={params['coef']['r']:.4f}, alpha={params['coef']['alpha']:.4f}, a={params['coef']['a']:.4f}, b={params['coef']['b']:.4f}")
        return self.bgf

    def fit_gamma_gamma_model(self) -> GammaGammaFitter:
        """
        Fits Gamma-Gamma model on customers with repeat purchases (frequency > 0).
        Estimates expected average order monetary values.
        """
        if self.rfm_summary is None:
            self.load_and_prepare_rfm()

        # Gamma-Gamma requires at least 1 repeat purchase
        returning_customers = self.rfm_summary[
            (self.rfm_summary["frequency"] > 0) & (self.rfm_summary["monetary_value"] > 0)
        ].copy()

        # Check correlation between frequency and monetary value (assumption check)
        corr = returning_customers["frequency"].corr(returning_customers["monetary_value"])
        print(f"[BTYD] Frequency vs Monetary Value Correlation: {corr:.4f} (Assumption holds if close to 0)")

        print(f"[BTYD] Fitting Gamma-Gamma Model on {len(returning_customers):,} returning accounts...")
        self.ggf = GammaGammaFitter(penalizer_coef=self.penalizer_coef)
        self.ggf.fit(returning_customers["frequency"], returning_customers["monetary_value"])

        params = self.ggf.summary
        print(f"[BTYD] Gamma-Gamma Parameters: p={params['coef']['p']:.4f}, q={params['coef']['q']:.4f}, v={params['coef']['v']:.4f}")
        return self.ggf

    def compute_clv(self, time_months: int = 12, discount_rate: float = 0.01) -> pd.DataFrame:
        """
        Computes 12-Month Net Present Value Customer Lifetime Value (CLV)
        and individual P(Alive) active probabilities.
        """
        if self.bgf is None:
            self.fit_bg_nbd_model()
        if self.ggf is None:
            self.fit_gamma_gamma_model()

        rfm = self.rfm_summary.copy()

        # 1. Continuous Probability of being Active / Alive right now
        rfm["P_Alive"] = self.bgf.conditional_probability_alive(
            rfm["frequency"], rfm["recency"], rfm["T"]
        ).round(4)

        # 2. Expected transactions in next 90 days (~12 weeks) and 365 days (~52 weeks)
        rfm["Expected_Orders_90d"] = self.bgf.conditional_expected_number_of_purchases_up_to_time(
            12.85, rfm["frequency"], rfm["recency"], rfm["T"]
        ).round(2)
        rfm["Expected_Orders_365d"] = self.bgf.conditional_expected_number_of_purchases_up_to_time(
            52.14, rfm["frequency"], rfm["recency"], rfm["T"]
        ).round(2)

        # 3. Expected average transaction value from Gamma-Gamma
        # For one-time buyers (frequency=0), fallback to population expected value
        expected_avg_spend = self.ggf.conditional_expected_average_profit(
            rfm["frequency"], rfm["monetary_value"]
        )
        rfm["Expected_Avg_Spend_GBP"] = expected_avg_spend.fillna(0.0).clip(lower=0.0).round(2)

        # 4. 12-Month Discounted Net Present Value CLV
        clv_12m = self.ggf.customer_lifetime_value(
            self.bgf,
            rfm["frequency"],
            rfm["recency"],
            rfm["T"],
            rfm["monetary_value"],
            time=time_months,
            discount_rate=discount_rate,
            freq="W"
        )
        rfm["CLV_12M_GBP"] = clv_12m.fillna(0.0).clip(lower=0.0).round(2)

        # 5. Customer CLV Portfolio Tiers
        def assign_tier(row):
            if row["P_Alive"] < 0.30:
                return "Lapsed / Dormant"
            elif row["CLV_12M_GBP"] >= 2500:
                return "Platinum VIP (High CLV)"
            elif row["CLV_12M_GBP"] >= 800:
                return "Gold Growth (Moderate CLV)"
            elif row["P_Alive"] >= 0.70:
                return "Active Core (Steady)"
            else:
                return "At-Risk Retention"

        rfm["CLV_Segment"] = rfm.apply(assign_tier, axis=1)

        # Reset index to have CustomerID as column
        results_df = rfm.reset_index().rename(columns={"index": "CustomerID"})
        self.clv_predictions = results_df.sort_values(by="CLV_12M_GBP", ascending=False).reset_index(drop=True)

        # Save artifacts
        DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        pq_out = DATA_PROCESSED_DIR / "customer_clv_predictions.parquet"
        csv_out = DATA_PROCESSED_DIR / "customer_clv_predictions.csv"
        results_df.to_parquet(pq_out, engine="pyarrow", compression="snappy", index=False)
        results_df.to_csv(csv_out, index=False)

        self.bgf.save_model(str(MODELS_DIR / "bgf_model.pkl"))
        self.ggf.save_model(str(MODELS_DIR / "ggf_model.pkl"))

        print(f"[BTYD] Saved CLV predictions ({len(results_df):,} customers) to {pq_out} and {csv_out}")
        print(f"[BTYD] Serialized BGF and GGF model binaries to {MODELS_DIR}")

        return self.clv_predictions


if __name__ == "__main__":
    clv_engine = BTYDCustomerLifetimeValue()
    clv_df = clv_engine.compute_clv(time_months=12, discount_rate=0.01)

    print("\n" + "="*80)
    print("TOP 10 CUSTOMERS BY 12-MONTH PREDICTED CLV (₹)")
    print("="*80)
    cols = ["CustomerID", "P_Alive", "Expected_Orders_365d", "Expected_Avg_Spend_GBP", "CLV_12M_GBP", "CLV_Segment"]
    print(clv_df[cols].head(10).to_string(index=False))

    print("\n" + "="*80)
    print("PORTFOLIO CLV SUMMARY BY SEGMENT")
    print("="*80)
    summary = clv_df.groupby("CLV_Segment").agg(
        Customers=("CustomerID", "count"),
        Avg_P_Alive=("P_Alive", "mean"),
        Total_CLV_GBP=("CLV_12M_GBP", "sum"),
        Avg_CLV_GBP=("CLV_12M_GBP", "mean")
    ).reset_index()
    summary["Total_CLV_Share_%"] = (summary["Total_CLV_GBP"] / summary["Total_CLV_GBP"].sum() * 100).round(2)
    summary["Avg_P_Alive"] = (summary["Avg_P_Alive"] * 100).round(1).astype(str) + "%"
    summary["Total_CLV_GBP"] = summary["Total_CLV_GBP"].round(2)
    summary["Avg_CLV_GBP"] = summary["Avg_CLV_GBP"].round(2)
    print(summary.to_string(index=False))

    print(f"\nTotal 12-Month Projected Portfolio Future Cash Flow: ₹{clv_df['CLV_12M_GBP'].sum():,.2f}")
