"""
Time-Series Feature Engineering for Daily E-Commerce Sales Forecasting.

Constructs autoregressive lag features, rolling window momentum statistics,
and temporal calendar signals to forecast daily revenue while strictly
preventing future lookahead data leakage.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
STORE_DATA_PATH = PROCESSED_DATA_DIR / "online_retail_cleaned.csv"


class SalesFeatureEngineer:
    """
    Transforms raw transactional logs into a clean, daily time-series feature store:
    - Target: Daily Gross Revenue (₹)
    - Autoregressive Lags: 1-day, 7-day (weekly cycle), 14-day, 30-day (monthly cycle)
    - Rolling Statistics: 7-day moving average, 7-day volatility (std), 30-day moving average
    - Calendar Features: Day of week, Month, Day of month, IsWeekend, Quarter
    """

    def __init__(self, data_path: Path = STORE_DATA_PATH, output_dir: Path = PROCESSED_DATA_DIR):
        self.data_path = data_path
        self.output_dir = output_dir
        self.df_raw: pd.DataFrame = None
        self.daily_df: pd.DataFrame = None

    def load_data(self) -> pd.DataFrame:
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Cleaned store dataset not found at {self.data_path}. Run clean.py first."
            )
        self.df_raw = pd.read_csv(
            self.data_path,
            parse_dates=["InvoiceDate"]
        )
        return self.df_raw

    def aggregate_daily_sales(self) -> pd.DataFrame:
        """Aggregates transactional line items to daily totals."""
        if self.df_raw is None:
            self.load_data()

        # Exclude cancellations and negative transactions for gross demand
        valid = self.df_raw[(~self.df_raw["IsCancelled"]) & (self.df_raw["Quantity"] > 0)].copy()

        daily = valid.groupby("Date").agg(
            DailyRevenue=("TotalPrice", "sum"),
            TotalOrders=("InvoiceNo", "nunique"),
            TotalQuantity=("Quantity", "sum"),
            UniqueCustomers=("CustomerID", "nunique")
        ).reset_index()

        daily["Date"] = pd.to_datetime(daily["Date"])
        daily = daily.sort_values(by="Date").reset_index(drop=True)

        # Ensure continuous daily date index (fill non-trading days, e.g. Christmas/closures, with 0)
        full_date_range = pd.date_range(start=daily["Date"].min(), end=daily["Date"].max(), freq="D")
        daily = daily.set_index("Date").reindex(full_date_range).fillna(0).reset_index()
        daily.rename(columns={"index": "Date"}, inplace=True)

        self.daily_df = daily
        print(f"[SalesFeatures] Continuous daily time series constructed: {len(self.daily_df)} days.")
        return self.daily_df

    def engineer_time_series_features(self) -> pd.DataFrame:
        """
        Creates lagged predictors and rolling windows.
        Note: Shifting ensures features use ONLY past historical information.
        """
        if self.daily_df is None:
            self.aggregate_daily_sales()

        df = self.daily_df.copy()

        # 1. Calendar / Temporal Features
        df["DayOfWeek"] = df["Date"].dt.dayofweek
        df["DayOfMonth"] = df["Date"].dt.day
        df["Month"] = df["Date"].dt.month
        df["Quarter"] = df["Date"].dt.quarter
        df["IsWeekend"] = df["DayOfWeek"].isin([5, 6]).astype(int)

        # 2. Autoregressive Lag Features (Shifted to prevent target leakage)
        df["Lag_1"] = df["DailyRevenue"].shift(1)
        df["Lag_2"] = df["DailyRevenue"].shift(2)
        df["Lag_7"] = df["DailyRevenue"].shift(7)    # Same day last week
        df["Lag_14"] = df["DailyRevenue"].shift(14)  # Fortnight lag
        df["Lag_30"] = df["DailyRevenue"].shift(30)  # Month lag

        # 3. Rolling Window Statistics (Shifted by 1 so current day target is excluded)
        df["RollingMean_7"] = df["DailyRevenue"].shift(1).rolling(window=7).mean()
        df["RollingStd_7"] = df["DailyRevenue"].shift(1).rolling(window=7).std()
        df["RollingMean_14"] = df["DailyRevenue"].shift(1).rolling(window=14).mean()
        df["RollingMean_30"] = df["DailyRevenue"].shift(1).rolling(window=30).mean()

        # 4. Lagged Volume Predictors
        df["LagOrders_1"] = df["TotalOrders"].shift(1)
        df["LagOrders_7"] = df["TotalOrders"].shift(7)

        # Drop initial rows with NaN from the 30-day lookback window
        df_clean = df.dropna().reset_index(drop=True)

        # Save processed daily dataset for modeling if output_dir provided
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            out_path = self.output_dir / "daily_sales_features.csv"
            out_pq = self.output_dir / "daily_sales_features.parquet"
            df_clean.to_csv(out_path, index=False)
            df_clean.to_parquet(out_pq, engine="pyarrow", compression="snappy", index=False)
            print(f"[SalesFeatures] Saved {len(df_clean)} feature-ready daily records to {out_path} and {out_pq}.")

        return df_clean


if __name__ == "__main__":
    fe = SalesFeatureEngineer()
    df_features = fe.engineer_time_series_features()
    print("\n--- SAMPLE ENGINEERED TIME-SERIES RECORD ---")
    print(df_features.tail(5)[["Date", "DailyRevenue", "Lag_1", "Lag_7", "RollingMean_7", "DayOfWeek", "Month"]])
