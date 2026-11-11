"""
Unit & Integration Tests for CSV/Excel Data Importer & Validation Engine.
"""

import io
import pytest
import pandas as pd
from pathlib import Path
import sys
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.data.importer import DatasetImporter, COLUMN_ALIASES
from src.api.server import app

client = TestClient(app)


def test_alias_mapping():
    """Assert flexible column matching identifies standard column variants."""
    raw_cols = ["Order_Number", "SKU", "Item_Name", "Units_Sold", "Order_Date", "Sales_Price", "Client_ID", "Market"]
    mapping, missing = DatasetImporter.match_columns(raw_cols)
    assert len(missing) == 0, f"Expected 0 missing required columns, got {missing}"
    assert mapping["Order_Number"] == "InvoiceNo"
    assert mapping["SKU"] == "StockCode"
    assert mapping["Units_Sold"] == "Quantity"
    assert mapping["Sales_Price"] == "UnitPrice"
    assert mapping["Order_Date"] == "InvoiceDate"
    assert mapping["Client_ID"] == "CustomerID"
    assert mapping["Market"] == "Country"


def test_missing_required_columns():
    """Assert validator rejects datasets missing mandatory fields."""
    incomplete_cols = ["Item_Name", "Units_Sold", "Market"]
    mapping, missing = DatasetImporter.match_columns(incomplete_cols)
    assert "InvoiceNo" in missing
    assert "StockCode" in missing
    assert "UnitPrice" in missing


def test_csv_and_excel_template_generation():
    """Assert template bytes generation creates valid CSV and openpyxl Excel bytes."""
    # CSV template
    csv_bytes, csv_mime, csv_fn = DatasetImporter.generate_template_bytes("csv")
    assert csv_mime == "text/csv"
    assert csv_fn.endswith(".csv")
    df_csv = pd.read_csv(io.BytesIO(csv_bytes))
    assert len(df_csv) > 0
    assert "InvoiceNo" in df_csv.columns

    # Excel template
    xlsx_bytes, xlsx_mime, xlsx_fn = DatasetImporter.generate_template_bytes("xlsx")
    assert "spreadsheetml" in xlsx_mime
    assert xlsx_fn.endswith(".xlsx")
    df_xlsx = pd.read_excel(io.BytesIO(xlsx_bytes), engine="openpyxl")
    assert len(df_xlsx) > 0
    assert "UnitPrice" in df_xlsx.columns


def test_validation_and_normalization():
    """Assert DatasetImporter computes accurate metrics and preview records."""
    df_sample = DatasetImporter.generate_sample_dataset(10)
    res = DatasetImporter.validate_and_normalize(df_sample, "test_orders.csv")
    assert res["valid"] is True
    assert res["total_rows_parsed"] == 10
    assert res["metrics"]["total_revenue_gbp"] > 0
    assert len(res["preview_rows"]) == 5


def test_api_download_template():
    """Assert GET /api/v1/data/download-template returns attachment responses."""
    # CSV
    res_csv = client.get("/api/v1/data/download-template?format=csv")
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    assert "attachment" in res_csv.headers["content-disposition"]

    # Excel
    res_xlsx = client.get("/api/v1/data/download-template?format=xlsx")
    assert res_xlsx.status_code == 200
    assert "spreadsheetml" in res_xlsx.headers["content-type"]


def test_api_demo_batch():
    """Assert GET /api/v1/data/demo-batch returns formatted test transactions."""
    res = client.get("/api/v1/data/demo-batch")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["data"]) >= 10


def test_api_validate_upload_endpoint():
    """Assert POST /api/v1/data/validate-upload parses uploaded file streams."""
    df_sample = DatasetImporter.generate_sample_dataset(8)
    csv_bytes = df_sample.to_csv(index=False).encode("utf-8")

    files = {"file": ("retail_import_test.csv", csv_bytes, "text/csv")}
    res = client.post("/api/v1/data/validate-upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["total_rows_parsed"] == 8
    assert "metrics" in data
    assert data["metrics"]["unique_orders"] > 0


def test_api_ingest_upload_endpoint():
    """Assert POST /api/v1/data/ingest-upload stores batch parquet and broadcasts metrics."""
    df_sample = DatasetImporter.generate_sample_dataset(6)
    csv_bytes = df_sample.to_csv(index=False).encode("utf-8")

    files = {"file": ("batch_test.csv", csv_bytes, "text/csv")}
    data_payload = {"merge_to_production": False, "trigger_retrain": False}
    res = client.post("/api/v1/data/ingest-upload", files=files, data=data_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert "batch_file" in data
    assert data["merged_to_production"] is False

