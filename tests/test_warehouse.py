"""
Verification Suite for Phase 25: Kimball Star-Schema Warehouse, SQL Workbench & DQ Suite.

Covers:
1. StarSchemaWarehouse deterministic synthetic build across 4 Dimensions & 2 Facts.
2. Automated 7-rule SQL Data-Quality contract certification (100% PASS, 0 violations).
3. Execution of curated analyst CTE / Window Function SQL case studies.
4. Strict read-only SQL sandbox rejection of DDL/DML injection & multi-statements.
5. FastAPI /api/v1/warehouse/schema, /data-quality, and /query endpoints.
"""

from fastapi.testclient import TestClient

from src.api.server import app
from src.data.warehouse import CASE_STUDY_QUERIES, StarSchemaWarehouse

client = TestClient(app)


def test_star_schema_dimensions_facts_and_dq_contracts():
    """Verify all 6 Kimball Star-Schema relations build and pass all 7 SQL DQ checks."""
    wh = StarSchemaWarehouse(use_parquet=False)
    assert wh.data_source == "synthetic_fallback"

    catalog = wh.get_schema_catalog()
    table_names = {t["table_name"] for t in catalog["tables"]}
    assert table_names == {
        "fact_order_lines",
        "fact_returns",
        "dim_customers",
        "dim_products",
        "dim_geography",
        "dim_date",
    }
    assert all(t["row_count"] > 0 for t in catalog["tables"])

    dq = wh.run_data_quality_checks()
    assert dq["status"] == "CERTIFIED_CLEAN"
    assert dq["score_pct"] == 100.0
    assert dq["passed_checks"] == 7
    assert all(c["violations"] == 0 for c in dq["checks"])


def test_warehouse_case_studies_and_readonly_sandbox_guard():
    """Verify every curated window-function case study executes and DDL/DML is blocked."""
    wh = StarSchemaWarehouse(use_parquet=False)

    for cs in CASE_STUDY_QUERIES:
        res = wh.execute_sql(cs["sql"], max_rows=50)
        assert res["status"] == "success"
        assert res["row_count"] >= 1
        assert len(res["columns"]) >= 2

    # Security block checks
    for bad_sql in [
        "DROP TABLE fact_order_lines",
        "DELETE FROM dim_customers WHERE customer_id = '14646'",
        "SELECT * FROM dim_date; DROP TABLE dim_products",
    ]:
        try:
            wh.execute_sql(bad_sql)
            assert False, f"Expected sandbox rejection for: {bad_sql}"
        except ValueError:
            pass


def test_api_warehouse_endpoints():
    """Verify FastAPI /warehouse/schema, /data-quality, and /query endpoints."""
    schema_res = client.get("/api/v1/warehouse/schema")
    assert schema_res.status_code == 200
    assert len(schema_res.json()["tables"]) == 6

    dq_res = client.get("/api/v1/warehouse/data-quality")
    assert dq_res.status_code == 200
    assert dq_res.json()["score_pct"] == 100.0

    q_res = client.post(
        "/api/v1/warehouse/query",
        json={"sql": "SELECT region, COUNT(*) AS countries FROM dim_geography GROUP BY 1 ORDER BY 2 DESC"},
    )
    assert q_res.status_code == 200
    assert q_res.json()["row_count"] >= 1

    bad_res = client.post(
        "/api/v1/warehouse/query",
        json={"sql": "DROP TABLE dim_geography"},
    )
    assert bad_res.status_code == 400
