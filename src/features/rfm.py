"""
RFM (Recency, Frequency, Monetary) Feature Engineering Module.

Calculates behavioral customer metrics and traditional quintile scores
to benchmark against unsupervised Machine Learning clustering.
"""

from pathlib import Path
import numpy as np
import pandas as pd

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
CUSTOMER_CENTRIC_PATH = PROCESSED_DATA_DIR / "online_retail_customer_centric.csv"


class RFMFeatureEngineer:
    """
    Transforms transactional logs into customer-level RFM features:
    - Recency (R): Days since last purchase relative to reference date.
    - Frequency (F): Number of unique orders/invoices placed.
    - Monetary (M): Total monetary spend across all transactions.
    - Tenure (T): Days between customer's first purchase and reference date.
    - AOV: Average Order Value (Monetary / Frequency).
    """

    def __init__(self, data_path: Path = CUSTOMER_CENTRIC_PATH):
        self.data_path = data_path
        self.df: pd.DataFrame = None
        self.rfm_df: pd.DataFrame = None

    def load_data(self) -> pd.DataFrame:
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Customer-centric data not found at {self.data_path}. Run clean.py first."
            )
        print(f"[RFM] Loading customer-centric transactions from {self.data_path}...")
        self.df = pd.read_csv(
            self.data_path,
            dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str},
            parse_dates=["InvoiceDate"]
        )
        return self.df

    def compute_rfm(self, reference_date: pd.Timestamp = None) -> pd.DataFrame:
        """
        Computes continuous RFM metrics for each unique customer.
        Reference date defaults to the day after the last invoice in the dataset.
        """
        if self.df is None:
            self.load_data()

        if reference_date is None:
            # Standard industry practice: 1 day after the latest transaction
            reference_date = self.df["InvoiceDate"].max() + pd.Timedelta(days=1)
        print(f"[RFM] Observation Reference Date: {reference_date}")

        rfm = self.df.groupby("CustomerID").agg(
            LastPurchaseDate=("InvoiceDate", "max"),
            FirstPurchaseDate=("InvoiceDate", "min"),
            Frequency=("InvoiceNo", "nunique"),
            Monetary=("TotalPrice", "sum"),
            TotalUnits=("Quantity", "sum")
        ).reset_index()

        # Recency: Days between last purchase and reference date
        rfm["Recency"] = (reference_date - rfm["LastPurchaseDate"]).dt.days

        # Tenure: Days between first purchase and reference date (Customer Lifetime Length)
        rfm["Tenure"] = (reference_date - rfm["FirstPurchaseDate"]).dt.days

        # Average Order Value (AOV)
        rfm["AOV"] = rfm["Monetary"] / rfm["Frequency"]

        # Drop temporary timestamp columns for clean feature store
        self.rfm_df = rfm[[
            "CustomerID", "Recency", "Frequency", "Monetary", "AOV", "Tenure", "TotalUnits"
        ]].copy()

        # Filter extreme zero or negative spend anomalies (if any residual exists)
        self.rfm_df = self.rfm_df[self.rfm_df["Monetary"] > 0].copy()

        print(f"[RFM] Computed RFM features for {len(self.rfm_df):,} customers.")
        return self.rfm_df

    def calculate_rfm_quintile_scores(self) -> pd.DataFrame:
        """
        Computes rule-based 1-5 RFM scores using quintiles (pd.qcut).
        - Recency: 5 is best (purchased recently), 1 is worst (purchased long ago).
        - Frequency: 5 is best (buys frequently), 1 is worst (rarely buys).
        - Monetary: 5 is best (high spender), 1 is worst (low spender).
        """
        if self.rfm_df is None:
            self.compute_rfm()

        df = self.rfm_df.copy()

        # Recency: Lower is better -> reverse rank [5, 4, 3, 2, 1]
        df["R_Score"] = pd.qcut(df["Recency"], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)

        # Frequency: Higher is better -> rank [1, 2, 3, 4, 5]
        # Frequency often has identical low values (e.g., 1 order), so rank with first/average method
        df["F_Score"] = pd.qcut(df["Frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]).astype(int)

        # Monetary: Higher is better -> rank [1, 2, 3, 4, 5]
        df["M_Score"] = pd.qcut(df["Monetary"], q=5, labels=[1, 2, 3, 4, 5]).astype(int)

        # Composite RFM Score (e.g. 555 is top tier champion)
        df["RFM_Score"] = df["R_Score"].astype(str) + df["F_Score"].astype(str) + df["M_Score"].astype(str)
        df["RFM_Index"] = df["R_Score"] + df["F_Score"] + df["M_Score"]

        self.rfm_df = df
        return self.rfm_df


if __name__ == "__main__":
    fe = RFMFeatureEngineer()
    rfm_table = fe.compute_rfm()
    fe.calculate_rfm_quintile_scores()
    print("\n--- RFM DESCRIPTIVE STATISTICS ---")
    print(rfm_table[["Recency", "Frequency", "Monetary", "AOV", "Tenure"]].describe().round(2))
    print("\n--- SAMPLE RFM SCORED CUSTOMERS ---")
    print(rfm_table[["CustomerID", "Recency", "Frequency", "Monetary", "RFM_Score", "RFM_Index"]].head())
