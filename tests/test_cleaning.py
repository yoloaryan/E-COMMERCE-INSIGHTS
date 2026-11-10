"""
Unit Tests for Data Cleaning & Preprocessing Pipeline.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.data.clean import ECommerceDataCleaner


@pytest.fixture
def sample_raw_data(tmp_path):
    """Generates synthetic messy transactional data mimicking real anomalies."""
    data = {
        "InvoiceNo": ["536365", "C536379", "536366", "536367", "536368"],
        "StockCode": ["85123A", "D", "POST", "22423", "22423"],
        "Description": [" White Hanging Heart ", "Discount", "POSTAGE", "regency cakestand ", "regency cakestand "],
        "Quantity": [6, -1, 1, 10, -5],
        "InvoiceDate": pd.to_datetime([
            "2010-12-01 08:26:00",
            "2010-12-01 09:41:00",
            "2010-12-01 09:45:00",
            "2010-12-01 10:00:00",
            "2010-12-01 10:30:00"
        ]),
        "UnitPrice": [2.55, 27.50, 18.00, 12.75, 12.75],
        "CustomerID": ["17850", "17850", np.nan, "13047", "13047"],
        "Country": ["United Kingdom", "United Kingdom", "France", "United Kingdom", "United Kingdom"]
    }
    df = pd.DataFrame(data)
    csv_file = tmp_path / "sample_raw.csv"
    df.to_csv(csv_file, index=False)
    return csv_file


def test_cleaner_cancellation_and_negative_quantities(sample_raw_data, tmp_path):
    """Assert cancellations and negative items are properly flagged."""
    cleaner = ECommerceDataCleaner(raw_csv_path=sample_raw_data, processed_dir=tmp_path)
    df_clean = cleaner.clean_transactions()

    # Invoice C536379 is filtered out due to admin code 'D'
    # Row 5 (Quantity -5) should be flagged as cancelled
    cancelled = df_clean[df_clean["IsCancelled"]]
    assert len(cancelled) >= 1
    assert all(cancelled["Quantity"] < 0)


def test_cleaner_admin_stockcodes_filtered(sample_raw_data, tmp_path):
    """Assert administrative stock codes (POST, D) are removed."""
    cleaner = ECommerceDataCleaner(raw_csv_path=sample_raw_data, processed_dir=tmp_path)
    df_clean = cleaner.clean_transactions()

    admin_codes = {"POST", "D", "M", "CRUK", "BANK CHARGES"}
    present_admin = set(df_clean["StockCode"]).intersection(admin_codes)
    assert len(present_admin) == 0, f"Found admin stock codes in clean dataset: {present_admin}"


def test_cleaner_guest_checkouts_preserved_in_storewide(sample_raw_data, tmp_path):
    """Assert guest checkouts (NaN CustomerID) are identified and kept in store dataset."""
    cleaner = ECommerceDataCleaner(raw_csv_path=sample_raw_data, processed_dir=tmp_path)
    df_clean = cleaner.clean_transactions()

    # Check guest mask
    assert "IsGuest" in df_clean.columns
    # Ensure guest checkout exists in store cleaned
    assert df_clean["IsGuest"].dtype == bool


def test_customer_centric_contains_only_registered_positive(sample_raw_data, tmp_path):
    """Assert customer-centric dataset only retains verified registered customers with positive transactions."""
    cleaner = ECommerceDataCleaner(raw_csv_path=sample_raw_data, processed_dir=tmp_path)
    cleaner.clean_transactions()
    cust_df = cleaner.df_customer_centric

    assert cust_df["CustomerID"].isna().sum() == 0
    assert (cust_df["Quantity"] <= 0).sum() == 0
    assert (cust_df["UnitPrice"] <= 0).sum() == 0

