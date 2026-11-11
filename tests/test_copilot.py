"""
Unit & Integration Tests for AI Copilot & Text-to-SQL Analytics Engine.
"""

import pytest
from pathlib import Path
import sys
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.api.copilot import RetailCopilot
from src.api.server import app

client = TestClient(app)


def test_copilot_top_products_intent():
    """Assert Copilot translates product questions to optimized DuckDB SQL."""
    copilot = RetailCopilot()
    res = copilot.execute_query("What are the top 3 products in Germany?")
    assert res["intent"] == "top_products"
    assert "sql" in res
    assert "Germany" in res["sql"]
    assert len(res["data"]) <= 3
    assert "GrossRevenueGBP" in res["columns"]
    assert res["execution_time_ms"] > 0


def test_copilot_churn_intent():
    """Assert Copilot identifies inactive accounts with high lifetime revenue."""
    copilot = RetailCopilot()
    res = copilot.execute_query("Show me top 5 accounts at risk of churn")
    assert res["intent"] == "churn_risk"
    assert len(res["data"]) <= 5
    assert "DaysInactive" in res["columns"]
    assert "LifetimeSpendGBP" in res["columns"]
    assert "concierge" in res["summary"].lower()


def test_copilot_customer_lookup_intent():
    """Assert Copilot recognizes explicit customer ID queries."""
    copilot = RetailCopilot()
    res = copilot.execute_query("History for customer #14096")
    assert res["intent"] == "customer_lookup"
    assert "14096" in res["sql"]
    assert len(res["data"]) == 1
    assert res["data"][0]["CustomerID"] == 14096


def test_copilot_countries_intent():
    """Assert Copilot computes country-level financial aggregations."""
    copilot = RetailCopilot()
    res = copilot.execute_query("What is our revenue breakdown by country?")
    assert res["intent"] == "geographic_markets"
    assert "Country" in res["columns"]
    assert len(res["data"]) > 0


def test_copilot_custom_sql_execution():
    """Assert Copilot safely executes read-only SELECT queries."""
    copilot = RetailCopilot()
    sql = "SELECT country, COUNT(*) as tx_count FROM ecommerce_transactions GROUP BY country ORDER BY tx_count DESC LIMIT 3;"
    res = copilot.execute_query(sql)
    assert res["intent"] == "custom_sql"
    assert len(res["data"]) == 3
    assert "tx_count" in res["columns"]


def test_copilot_security_sandbox_blocking():
    """Assert Copilot blocks write / destructive SQL operations."""
    copilot = RetailCopilot()
    res = copilot.execute_query("DROP TABLE ecommerce_transactions;")
    assert res["intent"] == "security_block"
    assert "Security restriction" in res["error"]
    assert len(res["data"]) == 0


def test_api_copilot_query_endpoint():
    """Assert POST /api/v1/copilot/query returns structured response."""
    payload = {"query": "Show me top 5 revenue products"}
    res = client.post("/api/v1/copilot/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "top_products"
    assert "summary" in data
    assert "data" in data
    assert len(data["data"]) > 0


def test_api_copilot_sample_prompts_endpoint():
    """Assert GET /api/v1/copilot/sample-prompts returns starter prompt categories."""
    res = client.get("/api/v1/copilot/sample-prompts")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert len(data["categories"]) >= 3
