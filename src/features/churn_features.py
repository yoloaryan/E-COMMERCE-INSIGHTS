"""
Customer Churn Feature Engineering Module.

Constructs an observation-window based feature store to train churn classification models
without temporal lookahead bias:
- Historical Feature Window: [Dataset Start to Cutoff Date]
- Future Churn Label Window: [Cutoff Date to Dataset End (90 days)]
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
STORE_DATA_PATH = PROCESSED_DATA_DIR / "online_retail_customer_centric.csv"


class ChurnFeatureEngineer:
    """
    Constructs an out-of-time churn prediction dataset:
    - Cutoff Date: MaxDate - 90 Days (~2011-09-10)
    - Target (Churn): 1 if customer placed 0 orders in the subsequent 90 days; 0 otherwise.
    - Features: Extracted strictly using transactions on or before Cutoff Date.
    """

    def __init__(self, data_path: Path = STORE_DATA_PATH, churn_window_days: int = 90):
        self.data_path = data_path
        self.churn_window_days = churn_window_days
        self.df: pd.DataFrame = None
        self.churn_dataset: pd.DataFrame = None

    def load_data(self) -> pd.DataFrame:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Processed dataset not found at {self.data_path}.")
        self.df = pd.read_csv(
            self.data_path,
            dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str},
            parse_dates=["InvoiceDate"]
        )
        return self.df

    def engineer_churn_features(self) -> pd.DataFrame:
        """
        Splits timeline into historical feature observation period and future label window.
        """
        if self.df is None:
            self.load_data()

        max_date = self.df["InvoiceDate"].max()
        cutoff_date = max_date - pd.Timedelta(days=self.churn_window_days)
        print(f"[Churn] Total Horizon: {self.df['InvoiceDate'].min().date()} to {max_date.date()}")
        print(f"[Churn] Observation Cutoff Date: {cutoff_date.date()}")
        print(f"[Churn] Future Evaluation Window: {cutoff_date.date()} to {max_date.date()} ({self.churn_window_days} days)")

        # 1. Historical transactions (strictly <= cutoff_date)
        hist_df = self.df[self.df["InvoiceDate"] <= cutoff_date].copy()

        # 2. Future transactions (strictly > cutoff_date)
        future_df = self.df[self.df["InvoiceDate"] > cutoff_date].copy()

        # Active customers prior to cutoff date
        hist_customers = hist_df["CustomerID"].unique()
        print(f"[Churn] Customers active prior to cutoff: {len(hist_customers):,}")

        # 3. Determine ground-truth Churn label:
        # Customers who made at least 1 purchase in future window
        future_active_customers = set(future_df["CustomerID"].unique())

        # 4. Compute Historical Features
        features = hist_df.groupby("CustomerID").agg(
            LastPurchase=("InvoiceDate", "max"),
            FirstPurchase=("InvoiceDate", "min"),
            HistoricalFrequency=("InvoiceNo", "nunique"),
            HistoricalMonetary=("TotalPrice", "sum"),
            HistoricalUnits=("Quantity", "sum"),
            UniqueSKUs=("StockCode", "nunique")
        ).reset_index()

        # Recency at cutoff: Days since last purchase relative to cutoff date
        features["Recency"] = (cutoff_date - features["LastPurchase"]).dt.days

        # Tenure at cutoff: Days since first purchase relative to cutoff date
        features["Tenure"] = (cutoff_date - features["FirstPurchase"]).dt.days

        # Average Order Value (AOV)
        features["AOV"] = features["HistoricalMonetary"] / features["HistoricalFrequency"]

        # Items per order
        features["UnitsPerOrder"] = features["HistoricalUnits"] / features["HistoricalFrequency"]

        # Inter-Purchase Interval Velocity (days per order)
        # Avoid division by zero: if frequency=1, interval = tenure
        features["PurchaseVelocity"] = np.where(
            features["HistoricalFrequency"] > 1,
            features["Tenure"] / (features["HistoricalFrequency"] - 1),
            features["Tenure"]
        )

        # 5. Attach Ground-Truth Churn Target
        # Churn = 1 (did NOT purchase in future 90 days), Churn = 0 (DID purchase)
        features["Churn"] = features["CustomerID"].apply(
            lambda cid: 0 if cid in future_active_customers else 1
        )

        # Drop raw dates
        clean_features = features[[
            "CustomerID", "Recency", "HistoricalFrequency", "HistoricalMonetary",
            "HistoricalUnits", "UniqueSKUs", "Tenure", "AOV", "UnitsPerOrder",
            "PurchaseVelocity", "Churn"
        ]].copy()

        out_path = PROCESSED_DATA_DIR / "customer_churn_features.csv"
        clean_features.to_csv(out_path, index=False)
        self.churn_dataset = clean_features

        churn_rate = (clean_features["Churn"].sum() / len(clean_features)) * 100
        print(f"[Churn] Feature dataset saved to {out_path} ({len(clean_features)} customers).")
        print(f"[Churn] Ground-Truth Churn Rate: {churn_rate:.2f}% ({clean_features['Churn'].sum()} churned, {len(clean_features) - clean_features['Churn'].sum()} retained).")

        return clean_features


if __name__ == "__main__":
    cfe = ChurnFeatureEngineer()
    df_churn = cfe.engineer_churn_features()
    print("\n--- SAMPLE CHURN FEATURE RECORDS ---")
    print(df_churn.head())
