"""
Data Cleaning & Preprocessing Pipeline for E-Commerce Customer Intelligence.

Transforms messy transactional logs into production-grade datasets for downstream
ML tasks (RFM Segmentation, Sales Forecasting, Churn Classification, Recommendations).
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
CSV_PATH = RAW_DATA_DIR / "online_retail.csv"


class ECommerceDataCleaner:
    """
    Robust cleaning engine addressing real-world transactional anomalies:
    1. Null CustomerIDs (Guest checkout vs Registered accounts).
    2. Cancellations (InvoiceNo prefixed with 'C' and negative quantities).
    3. Non-product administrative SKUs (POST, D, M, BANK CHARGES, AMAZON FEE).
    4. Outlier detection and price validation.
    """

    ADMIN_STOCK_CODES = {
        "POST", "D", "M", "PADS", "DOT", "CRUK",
        "BANK CHARGES", "AMAZONFEE", "S", "B"
    }

    def __init__(self, raw_csv_path: Path = CSV_PATH):
        self.raw_csv_path = raw_csv_path
        self.df_raw: pd.DataFrame = None
        self.df_cleaned: pd.DataFrame = None
        self.df_customer_centric: pd.DataFrame = None

    def load_data(self) -> pd.DataFrame:
        """Load raw CSV data with appropriate schema parsing."""
        if not self.raw_csv_path.exists():
            raise FileNotFoundError(
                f"Raw CSV not found at {self.raw_csv_path}. Run ingest.py first."
            )
        print(f"[Cleaner] Loading raw transactions from {self.raw_csv_path}...")
        self.df_raw = pd.read_csv(
            self.raw_csv_path,
            dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str},
            parse_dates=["InvoiceDate"]
        )
        print(f"[Cleaner] Loaded {len(self.df_raw):,} records across {self.df_raw.shape[1]} columns.")
        return self.df_raw

    def clean_transactions(self) -> pd.DataFrame:
        """
        Executes full preprocessing pipeline.
        Returns cleaned DataFrame suitable for aggregate sales forecasting.
        """
        if self.df_raw is None:
            self.load_data()

        df = self.df_raw.copy()

        # 1. Clean StockCodes & Descriptions
        df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
        df["Description"] = df["Description"].astype(str).str.strip().str.title()

        # 2. Flag Cancellations
        df["IsCancelled"] = df["InvoiceNo"].str.startswith("C", na=False) | (df["Quantity"] < 0)

        # 3. Clean UnitPrice & Quantity
        # Filter out negative or zero unit prices (administrative adjustments / debt write-offs)
        valid_price_mask = df["UnitPrice"] > 0
        df = df[valid_price_mask].copy()

        # 4. Filter out administrative non-inventory stock codes
        df = df[~df["StockCode"].isin(self.ADMIN_STOCK_CODES)].copy()

        # 5. Handle Guest Checkouts vs Registered Customers
        df["IsGuest"] = df["CustomerID"].isna()

        # 6. Calculate Line-Item Financial Metrics
        df["TotalPrice"] = df["Quantity"] * df["UnitPrice"]

        # 7. Extract Temporal Features
        df["InvoiceYear"] = df["InvoiceDate"].dt.year
        df["InvoiceMonth"] = df["InvoiceDate"].dt.month
        df["InvoiceDay"] = df["InvoiceDate"].dt.day
        df["DayOfWeek"] = df["InvoiceDate"].dt.day_name()
        df["Hour"] = df["InvoiceDate"].dt.hour
        df["YearMonth"] = df["InvoiceDate"].dt.to_period("M").astype(str)
        df["Date"] = df["InvoiceDate"].dt.date

        # Separate completed positive sales from cancellations
        # For sales volume and revenue analysis, positive transactions reflect actual gross receipts
        self.df_cleaned = df

        # Save store-wide transactional dataset (includes guest checkouts for macro sales forecasting)
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        store_csv_path = PROCESSED_DATA_DIR / "online_retail_cleaned.csv"
        df.to_csv(store_csv_path, index=False)
        print(f"[Cleaner] Saved store-wide cleaned dataset ({len(df):,} rows) to: {store_csv_path}")

        # 8. Customer-Centric Sub-dataset (Registered Customers Only, Non-Cancelled for RFM/Churn/RecSys)
        customer_df = df[
            (~df["IsGuest"]) &
            (~df["IsCancelled"]) &
            (df["Quantity"] > 0)
        ].copy()
        customer_df["CustomerID"] = customer_df["CustomerID"].astype(float).astype(int).astype(str)

        self.df_customer_centric = customer_df
        cust_csv_path = PROCESSED_DATA_DIR / "online_retail_customer_centric.csv"
        customer_df.to_csv(cust_csv_path, index=False)
        print(f"[Cleaner] Saved customer-centric dataset ({len(customer_df):,} rows, {customer_df['CustomerID'].nunique():,} unique customers) to: {cust_csv_path}")

        return self.df_cleaned

    def generate_audit_summary(self) -> dict:
        """Returns key sanity audit metrics comparing raw vs cleaned."""
        if self.df_cleaned is None or self.df_customer_centric is None:
            self.clean_transactions()

        return {
            "raw_record_count": len(self.df_raw),
            "cleaned_record_count": len(self.df_cleaned),
            "customer_centric_count": len(self.df_customer_centric),
            "unique_customers": self.df_customer_centric["CustomerID"].nunique(),
            "unique_products": self.df_customer_centric["StockCode"].nunique(),
            "date_range_start": str(self.df_cleaned["InvoiceDate"].min()),
            "date_range_end": str(self.df_cleaned["InvoiceDate"].max()),
            "cancellations_count": int(self.df_cleaned["IsCancelled"].sum()),
            "guest_checkouts_count": int(self.df_cleaned["IsGuest"].sum()),
            "gross_revenue": float(self.df_customer_centric["TotalPrice"].sum())
        }


if __name__ == "__main__":
    cleaner = ECommerceDataCleaner()
    cleaner.load_data()
    cleaner.clean_transactions()
    summary = cleaner.generate_audit_summary()
    print("\n--- DATA AUDIT SUMMARY ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")
