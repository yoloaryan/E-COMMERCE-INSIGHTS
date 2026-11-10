"""
Unit Tests for Probabilistic BTYD Customer Lifetime Value (CLV) Engine.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.models.clv_btyd import BTYDCustomerLifetimeValue

MODELS_DIR = ROOT_DIR / "models"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"


def test_clv_artifacts_exist():
    """Asserts BTYD model binaries and prediction tables exist on disk."""
    bgf_path = MODELS_DIR / "bgf_model.pkl"
    ggf_path = MODELS_DIR / "ggf_model.pkl"
    pq_path = DATA_PROCESSED_DIR / "customer_clv_predictions.parquet"

    assert bgf_path.exists(), "BGF model artifact missing"
    assert ggf_path.exists(), "GGF model artifact missing"
    assert pq_path.exists(), "CLV prediction dataset missing"


def test_clv_prediction_bounds():
    """Asserts P(Alive) is within [0, 1] and 12M CLV values are non-negative."""
    pq_path = DATA_PROCESSED_DIR / "customer_clv_predictions.parquet"
    df = pd.read_parquet(pq_path)

    assert len(df) == 4334
    assert df["P_Alive"].min() >= 0.0
    assert df["P_Alive"].max() <= 1.0
    assert df["CLV_12M_GBP"].min() >= 0.0
    assert df["CLV_12M_GBP"].sum() > 5000000.0  # Multi-million expected portfolio cash flow


def test_clv_segments_distribution():
    """Asserts expected BTYD customer lifetime value segments are present."""
    pq_path = DATA_PROCESSED_DIR / "customer_clv_predictions.parquet"
    df = pd.read_parquet(pq_path)

    expected_segments = {"Platinum VIP (High CLV)", "Gold Growth (Moderate CLV)", "Active Core (Steady)"}
    found_segments = set(df["CLV_Segment"].unique())
    assert expected_segments.issubset(found_segments)

