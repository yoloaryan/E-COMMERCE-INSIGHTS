"""
Unit Tests for Feature Engineering Pipelines (RFM, Time-Series Lags, Churn Observation Window).
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.features.rfm import RFMFeatureEngineer
from src.features.sales_features import SalesFeatureEngineer
from src.features.churn_features import ChurnFeatureEngineer


@pytest.fixture
def sample_customer_transactions(tmp_path):
    """Generates synthetic customer transactions across two dates."""
    data = {
        "InvoiceNo": ["1001", "1002", "1003", "1004"],
        "StockCode": ["A1", "A2", "A1", "B1"],
        "Quantity": [2, 5, 1, 10],
        "UnitPrice": [10.0, 20.0, 10.0, 5.0],
        "CustomerID": ["C1", "C1", "C2", "C3"],
        "InvoiceDate": pd.to_datetime([
            "2011-01-01 10:00:00",
            "2011-01-05 12:00:00",
            "2011-01-02 11:00:00",
            "2011-01-06 14:00:00"
        ]),
        "TotalPrice": [20.0, 100.0, 10.0, 50.0]
    }
    df = pd.DataFrame(data)
    csv_file = tmp_path / "sample_cust.csv"
    df.to_csv(csv_file, index=False)
    return csv_file


def test_rfm_calculation_logic(sample_customer_transactions):
    """Verifies RFM feature math and bounds."""
    fe = RFMFeatureEngineer(data_path=sample_customer_transactions)
    ref_date = pd.Timestamp("2011-01-07 12:00:00")
    rfm = fe.compute_rfm(reference_date=ref_date)

    assert len(rfm) == 3  # C1, C2, C3

    # C1 placed 2 orders (1001, 1002), total spend = 120.0, last order on Jan 5 12:00 -> recency = 2 days
    c1 = rfm[rfm["CustomerID"] == "C1"].iloc[0]
    assert c1["Frequency"] == 2
    assert c1["Monetary"] == 120.0
    assert c1["Recency"] == 2
    assert c1["AOV"] == 60.0


def test_time_series_lags_prevent_future_leakage():
    """Asserts that lag_1 matches previous day revenue and does not leak current day."""
    dates = pd.date_range("2011-01-01", periods=15, freq="D")
    daily = pd.DataFrame({
        "Date": dates,
        "TotalPrice": [100.0 * (i + 1) for i in range(15)],
        "InvoiceNo": [f"INV_{i}" for i in range(15)],
        "Quantity": [10] * 15,
        "CustomerID": [f"C_{i}" for i in range(15)],
        "IsCancelled": [False] * 15
    })
    
    fe = SalesFeatureEngineer()
    fe.df_raw = daily
    daily_agg = fe.aggregate_daily_sales()
    
    # Check that Lag_1 on day t equals DailyRevenue on day t-1
    fe.daily_df = daily_agg
    df_feat = fe.engineer_time_series_features()
    
    # Lag_1 must equal previous day's DailyRevenue
    for idx in range(1, len(df_feat)):
        prev_rev = daily_agg.loc[daily_agg["Date"] == df_feat.loc[idx, "Date"] - pd.Timedelta(days=1), "DailyRevenue"].values[0]
        assert df_feat.loc[idx, "Lag_1"] == prev_rev
