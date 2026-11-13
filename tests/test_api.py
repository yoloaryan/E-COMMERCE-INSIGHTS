"""
Integration Tests for FastAPI ML Serving Layer.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.api.server import app

client = TestClient(app)


def test_api_root_and_health():
    """Assert root and health endpoints return 200 OK and valid status."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["service"] == "Prism Retail Serving API"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"


def test_forecast_sales_endpoint():
    """Assert sales forecast endpoint returns non-negative revenue prediction."""
    payload = {
        "DayOfWeek": 3,
        "DayOfMonth": 15,
        "Month": 10,
        "Quarter": 4,
        "IsWeekend": 0,
        "Lag_1": 42000.0,
        "Lag_2": 39000.0,
        "Lag_7": 45000.0,
        "Lag_14": 41000.0,
        "Lag_30": 38000.0,
        "RollingMean_7": 41500.0,
        "RollingStd_7": 3200.0,
        "RollingMean_14": 40800.0,
        "RollingMean_30": 39500.0,
        "LagOrders_1": 120.0,
        "LagOrders_7": 115.0
    }
    res = client.post("/api/v1/forecast/sales", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "predicted_daily_revenue_gbp" in data
    assert data["predicted_daily_revenue_gbp"] >= 0.0


def test_churn_prediction_endpoint():
    """Assert churn risk scoring returns valid probabilities and risk tiers."""
    payload = {
        "Recency": 120.0,
        "HistoricalFrequency": 2.0,
        "HistoricalMonetary": 350.0,
        "HistoricalUnits": 45.0,
        "UniqueSKUs": 12.0,
        "Tenure": 240.0,
        "AOV": 175.0,
        "UnitsPerOrder": 22.5,
        "PurchaseVelocity": 0.25
    }
    res = client.post("/api/v1/churn/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["risk_tier"] in ["High Risk", "Elevated Risk", "Medium Risk", "Low Risk (Healthy)"]
    assert "recommended_strategy" in data


def test_recommender_endpoint():
    """Assert cross-sell recommendations return top-5 complementary SKUs."""
    # Test valid SKU: 22423 (Regency Cakestand)
    res = client.get("/api/v1/recommend/item/22423?top_n=5")
    assert res.status_code == 200
    data = res.json()
    assert data["query_stock_code"] == "22423"
    assert len(data["recommendations"]) == 5
    assert data["is_cold_start_fallback"] is False

    # Test unknown SKU (Cold-start fallback)
    cold_res = client.get("/api/v1/recommend/item/UNKNOWN_SKU?top_n=3")
    assert cold_res.status_code == 200
    cold_data = cold_res.json()
    assert cold_data["is_cold_start_fallback"] is True
    assert len(cold_data["recommendations"]) == 3


def test_segmentation_endpoint():
    """Assert RFM categorization outputs valid behavioral persona."""
    payload = {
        "Recency": 10.0,
        "Frequency": 15,
        "Monetary": 6500.0
    }
    res = client.post("/api/v1/segment/rfm", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "segment_name" in data
    assert data["cluster_id"] in [0, 1, 2, 3]


def test_analytics_kpi_endpoint():
    """Assert DuckDB live KPI endpoint returns valid financial aggregations."""
    res = client.get("/api/v1/analytics/kpis")
    assert res.status_code == 200
    data = res.json()
    assert data["total_gross_revenue_gbp"] > 1000000.0
    assert data["total_completed_orders"] > 10000
    assert len(data["top_revenue_products"]) > 0


def test_clv_endpoints():
    """Assert BTYD CLV summary and customer lookup endpoints return expected structures."""
    # Summary
    summary_res = client.get("/api/v1/clv/summary")
    assert summary_res.status_code == 200
    sum_data = summary_res.json()
    assert sum_data["total_12m_portfolio_clv_gbp"] > 5000000.0
    assert len(sum_data["segments"]) > 0

    # Specific Customer Lookup (Customer 14646 is a verified VIP)
    cust_res = client.get("/api/v1/clv/customer/14646")
    assert cust_res.status_code == 200
    cust_data = cust_res.json()
    assert cust_data["customer_id"] == "14646"
    assert cust_data["p_alive"] > 0.8
    assert cust_data["clv_12m_gbp"] > 10000.0
    assert "Platinum VIP" in cust_data["clv_segment"]


def test_order_injection_and_streaming():
    """Assert POS order injection calculates totals, reactive churn drop, and stream status."""
    payload = {
        "customer_id": "14096",
        "country": "United Kingdom",
        "items": [
            {
                "stock_code": "22423",
                "description": "Regency Cakestand 3 Tier",
                "quantity": 10,
                "unit_price": 10.95
            },
            {
                "stock_code": "85123A",
                "description": "White Hanging Heart T-Light Holder",
                "quantity": 20,
                "unit_price": 2.55
            }
        ]
    }
    res = client.post("/api/v1/orders/inject", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    order = data["order"]
    assert order["customer_id"] == "14096"
    assert order["total_amount_gbp"] == 160.50  # (10 * 10.95) + (20 * 2.55) = 109.50 + 51.00 = 160.50
    assert order["total_units"] == 30
    assert order["updated_churn_probability"] < 0.20
    assert order["updated_recency_days"] == 0

    # Stream Status
    status_res = client.get("/api/v1/orders/stream-status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "online"

    # WebSocket connection test
    with client.websocket_connect("/ws/live-orders") as websocket:
        initial = websocket.receive_json()
        assert initial["type"] == "CONNECTION_ESTABLISHED"
        websocket.send_text('{"action": "ping"}')
        pong = websocket.receive_json()
        assert pong["type"] == "PONG"

