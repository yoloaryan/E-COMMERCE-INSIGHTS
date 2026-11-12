"""
Verification Suite for Phase 23: Live Executive Boardroom Briefing & Export Pipeline.

Covers:
1. ExecutiveBriefingGenerator 6-engine aggregation (Financial Waterfall, Cohort Retention,
   Inventory EOQ, Market Basket Rules, Autonomous Watchdog, and SQLite Persistence).
2. Markdown board memo formatting completeness.
3. FastAPI /api/v1/reports/executive-briefing and /download attachment endpoints (.md & .json).
"""

from fastapi.testclient import TestClient

from src.api.briefing import ExecutiveBriefingGenerator
from src.api.server import app

client = TestClient(app)


def test_executive_briefing_six_engine_aggregation():
    """Verify live aggregation populates all 4 headline KPIs and 5 subsystem audit rows."""
    briefing = ExecutiveBriefingGenerator.generate_briefing(country="All", cogs_ratio=0.58)
    assert briefing["status"] == "success"
    assert len(briefing["headline_kpis"]) == 4
    assert len(briefing["engine_audit_rows"]) == 5
    assert 0.0 <= float(briefing["executive_health_score"]) <= 100.0
    assert len(briefing["strategic_directives"]) >= 1

    memo = ExecutiveBriefingGenerator.render_markdown_memo(briefing)
    assert "# Nexus Retail AI — Executive Boardroom Briefing" in memo
    assert "## 1. Headline Financial & Intelligence KPIs" in memo
    assert "## 3. Prioritized Board Strategic Directives" in memo
    assert "£" in memo


def test_api_executive_briefing_and_downloads():
    """Verify JSON briefing and attachment download endpoints (.md and .json)."""
    res = client.get("/api/v1/reports/executive-briefing?country=United%20Kingdom")
    assert res.status_code == 200
    data = res.json()
    assert data["country"] == "United Kingdom"
    assert len(data["engine_audit_rows"]) == 5

    dl_md = client.get("/api/v1/reports/executive-briefing/download?format=markdown")
    assert dl_md.status_code == 200
    assert "attachment" in dl_md.headers.get("content-disposition", "")
    assert "nexus_executive_briefing.md" in dl_md.headers.get("content-disposition", "")
    assert "# Nexus Retail AI" in dl_md.text

    dl_json = client.get("/api/v1/reports/executive-briefing/download?format=json")
    assert dl_json.status_code == 200
    assert "nexus_executive_briefing.json" in dl_json.headers.get("content-disposition", "")
    assert dl_json.json()["status"] == "success"

