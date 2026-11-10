"""
Unit Tests for Machine Learning Models & Inference Invariants.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import joblib

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

MODELS_DIR = ROOT_DIR / "models"


def test_kmeans_rfm_model_artifact():
    """Asserts KMeans clustering model and scaler load and produce valid cluster labels."""
    kmeans_path = MODELS_DIR / "kmeans_rfm_model.joblib"
    scaler_path = MODELS_DIR / "rfm_scaler.joblib"

    assert kmeans_path.exists(), "KMeans model artifact not found"
    assert scaler_path.exists(), "RFM Scaler artifact not found"

    kmeans = joblib.load(kmeans_path)
    scaler = joblib.load(scaler_path)

    # 4 clusters expected
    assert kmeans.n_clusters == 4

    # Test dummy RFM record: Recency=10, Frequency=5, Monetary=1500
    sample_input = pd.DataFrame([[10, 5, 1500.0]], columns=["Recency", "Frequency", "Monetary"])
    scaled = scaler.transform(np.log1p(sample_input))
    cluster = kmeans.predict(scaled)

    assert cluster[0] in [0, 1, 2, 3]


def test_sales_forecaster_artifact():
    """Asserts sales forecasting model produces non-negative predictions."""
    model_path = MODELS_DIR / "best_sales_forecaster.joblib"
    assert model_path.exists(), "Sales forecaster artifact not found"

    model = joblib.load(model_path)
    from src.models.sales_forecasting import SalesForecastingPipeline
    dummy_features = pd.DataFrame(np.ones((1, len(SalesForecastingPipeline.FEATURE_COLS))), columns=SalesForecastingPipeline.FEATURE_COLS)
    pred = model.predict(dummy_features)

    assert len(pred) == 1
    assert pred[0] >= 0.0


def test_churn_classifier_artifact():
    """Asserts churn classifier outputs valid probabilities in [0.0, 1.0]."""
    model_path = MODELS_DIR / "best_churn_classifier.joblib"
    scaler_path = MODELS_DIR / "churn_scaler.joblib"

    assert model_path.exists(), "Churn classifier artifact not found"
    assert scaler_path.exists(), "Churn scaler artifact not found"

    model = joblib.load(model_path)
    from src.models.churn_prediction import CustomerChurnPredictor
    dummy_features = pd.DataFrame([[30, 5, 500.0, 100, 20, 180, 100.0, 20.0, 1.5]], columns=CustomerChurnPredictor.FEATURE_COLS)
    proba = model.predict_proba(dummy_features)[:, 1]

    assert 0.0 <= proba[0] <= 1.0
