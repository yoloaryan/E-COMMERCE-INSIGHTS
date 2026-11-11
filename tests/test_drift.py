"""
Unit & Integration Tests for Statistical Data Drift Detection and Retraining Engine.
"""

import pytest
import numpy as np
from pathlib import Path
import sys
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.models.drift_monitor import calculate_psi, calculate_ks, DataDriftMonitor
from src.api.server import app

client = TestClient(app)


def test_calculate_psi_identical_distributions():
    """Assert PSI between two samples of the same normal distribution is negligible (< 0.10)."""
    np.random.seed(42)
    ref = np.random.normal(50, 10, 2000)
    curr = np.random.normal(50, 10, 2000)
    psi = calculate_psi(ref, curr, num_buckets=10)
    assert psi < 0.05, f"Expected negligible PSI for identical distributions, got {psi}"


def test_calculate_psi_shifted_distributions():
    """Assert PSI captures significant population shift (> 0.25)."""
    np.random.seed(42)
    ref = np.random.normal(50, 10, 2000)
    # Substantial distribution shift
    curr = np.random.normal(85, 15, 2000)
    psi = calculate_psi(ref, curr, num_buckets=10)
    assert psi > 0.25, f"Expected PSI > 0.25 for heavily shifted distributions, got {psi}"


def test_calculate_ks_statistical_divergence():
    """Assert Kolmogorov-Smirnov test identifies identical vs drifted populations."""
    np.random.seed(42)
    ref = np.random.exponential(scale=10.0, size=1500)
    curr_same = np.random.exponential(scale=10.0, size=1500)
    curr_drift = np.random.exponential(scale=35.0, size=1500)

    ks_same = calculate_ks(ref, curr_same)
    assert ks_same["p_value"] > 0.05
    assert ks_same["ks_statistic"] < 0.1

    ks_drift = calculate_ks(ref, curr_drift)
    assert ks_drift["p_value"] < 0.001
    assert ks_drift["ks_statistic"] > 0.2


def test_drift_monitor_baseline_and_scenarios():
    """Assert DataDriftMonitor handles baseline and extreme event scenarios accurately."""
    monitor = DataDriftMonitor()
    
    # 1. Baseline scenario
    report_baseline = monitor.generate_drift_report(scenario="baseline")
    assert report_baseline["scenario"] == "baseline"
    assert report_baseline["overall_status"] in ["HEALTHY", "WARNING"]
    assert report_baseline["drift_detected_count"] == 0
    assert "features" in report_baseline
    feature_names = [f["feature"] for f in report_baseline["features"]]
    assert "Quantity" in feature_names

    # 2. Black Friday surge
    report_bf = monitor.generate_drift_report(scenario="black_friday")
    assert report_bf["scenario"] == "black_friday"
    assert report_bf["overall_status"] == "DRIFT_DETECTED"
    assert report_bf["drift_detected_count"] > 0
    bf_qty = next(f for f in report_bf["features"] if f["feature"] == "Quantity")
    assert bf_qty["status"] == "DRIFT_DETECTED"
    assert bf_qty["psi_score"] > 0.25

    # 3. Inflation scenario
    report_inf = monitor.generate_drift_report(scenario="inflation")
    assert report_inf["scenario"] == "inflation"
    assert report_inf["overall_status"] == "DRIFT_DETECTED"
    inf_price = next(f for f in report_inf["features"] if f["feature"] == "UnitPrice")
    assert inf_price["status"] == "DRIFT_DETECTED"
    assert inf_price["psi_score"] > 0.25


def test_api_drift_report_endpoint():
    """Assert GET /api/v1/mlops/drift-report returns structured drift telemetry."""
    # Test default baseline
    res = client.get("/api/v1/mlops/drift-report")
    assert res.status_code == 200
    data = res.json()
    assert "overall_status" in data
    assert "features" in data
    feature_names = [f["feature"] for f in data["features"]]
    assert "UnitPrice" in feature_names
    assert "Quantity" in feature_names
    assert "TotalPrice" in feature_names

    # Test Black Friday scenario
    res_bf = client.get("/api/v1/mlops/drift-report?scenario=black_friday")
    assert res_bf.status_code == 200
    data_bf = res_bf.json()
    assert data_bf["scenario"] == "black_friday"
    assert data_bf["overall_status"] == "DRIFT_DETECTED"
    assert data_bf["drift_detected_count"] > 0


def test_api_mlops_retrain_endpoint():
    """Assert POST /api/v1/mlops/retrain triggers manifest update and returns valid metadata."""
    payload = {
        "trigger_source": "test_suite",
        "model_types": ["all"]
    }
    res = client.post("/api/v1/mlops/retrain", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "telemetry" in data
    telemetry = data["telemetry"]
    assert "retrained_at" in telemetry
    assert "new_version" in telemetry
    assert "models_retrained" in telemetry
    assert len(telemetry["models_retrained"]) >= 4

    # Verify manifest file exists and is populated
    manifest_path = ROOT_DIR / "models" / "model_manifest.json"
    assert manifest_path.exists()
