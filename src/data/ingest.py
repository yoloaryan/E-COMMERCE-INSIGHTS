"""
Data Ingestion Module for E-Commerce Customer Intelligence System.

Handles downloading, extracting, and converting the raw UCI Online Retail dataset
from Excel (.xlsx) to optimized CSV and Parquet formats for high-throughput analytics.
"""

import os
import zipfile
import urllib.request
from pathlib import Path
import pandas as pd


RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
DATASET_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
ZIP_PATH = RAW_DATA_DIR / "online_retail.zip"
XLSX_PATH = RAW_DATA_DIR / "Online Retail.xlsx"
CSV_PATH = RAW_DATA_DIR / "online_retail.csv"


def download_dataset(url: str = DATASET_URL, target_zip: Path = ZIP_PATH) -> Path:
    """Download the raw dataset zip archive from UCI repository if not already present."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not target_zip.exists():
        print(f"[Ingest] Downloading raw dataset from {url}...")
        urllib.request.urlretrieve(url, target_zip)
        print(f"[Ingest] Downloaded archive to: {target_zip}")
    else:
        print(f"[Ingest] Archive already exists at: {target_zip}")
    return target_zip


def extract_dataset(zip_path: Path = ZIP_PATH, extract_to: Path = RAW_DATA_DIR) -> Path:
    """Extract .xlsx from downloaded zip archive."""
    if not XLSX_PATH.exists():
        print(f"[Ingest] Extracting {zip_path}...")
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_to)
        print(f"[Ingest] Extracted raw excel file to: {XLSX_PATH}")
    else:
        print(f"[Ingest] Raw excel file already exists at: {XLSX_PATH}")
    return XLSX_PATH


def convert_xlsx_to_csv(xlsx_path: Path = XLSX_PATH, csv_path: Path = CSV_PATH) -> pd.DataFrame:
    """Convert Excel file to CSV to speed up future loading times from ~45s to <2s."""
    if csv_path.exists():
        print(f"[Ingest] Loading cached CSV from: {csv_path}")
        df = pd.read_csv(csv_path, parse_dates=["InvoiceDate"])
    else:
        print(f"[Ingest] Parsing Excel workbook from {xlsx_path} (this takes ~30 seconds)...")
        df = pd.read_excel(xlsx_path, engine="openpyxl")
        print(f"[Ingest] Successfully parsed {len(df):,} records. Saving to CSV at {csv_path}...")
        df.to_csv(csv_path, index=False)
        print(f"[Ingest] CSV conversion complete.")
    return df


if __name__ == "__main__":
    download_dataset()
    extract_dataset()
    df_raw = convert_xlsx_to_csv()
    print(f"[Ingest] Raw Data Shape: {df_raw.shape}")
    print(f"[Ingest] Columns: {list(df_raw.columns)}")
    print(df_raw.head())
