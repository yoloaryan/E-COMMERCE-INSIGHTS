"""
Dataset Ingestion & Flexible Schema Import Engine.

Supports ingesting transactional retail datasets in CSV, TSV, and Excel (.xlsx, .xls) formats,
with intelligent column aliasing, schema validation, data hygiene checks, and template generation.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import io
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd


# Flexible column aliasing map for standard retail schemas
COLUMN_ALIASES: Dict[str, List[str]] = {
    "InvoiceNo": [
        "invoiceno", "invoice_no", "invoice", "invoicenum", "invoice_number",
        "order_id", "orderid", "order_number", "bill_no", "bill_number",
        "transaction_id", "trans_id", "reference"
    ],
    "StockCode": [
        "stockcode", "stock_code", "sku", "product_id", "productid",
        "item_code", "item_id", "part_number", "code", "product_code"
    ],
    "Description": [
        "description", "desc", "product_name", "item_name", "product_title",
        "title", "item_desc", "name", "product"
    ],
    "Quantity": [
        "quantity", "qty", "units", "units_sold", "volume", "count",
        "item_count", "pieces", "amount"
    ],
    "InvoiceDate": [
        "invoicedate", "invoice_date", "date", "order_date", "timestamp",
        "datetime", "transaction_date", "created_at", "time"
    ],
    "UnitPrice": [
        "unitprice", "unit_price", "price", "rate", "cost", "item_price",
        "unit_cost", "sales_price", "retail_price"
    ],
    "CustomerID": [
        "customerid", "customer_id", "cust_id", "client_id", "user_id",
        "account_id", "buyer_id", "member_id", "customer"
    ],
    "Country": [
        "country", "region", "nation", "market", "territory", "location", "state"
    ]
}

REQUIRED_CANONICAL_COLUMNS = ["InvoiceNo", "StockCode", "Quantity", "InvoiceDate", "UnitPrice"]
OPTIONAL_CANONICAL_COLUMNS = ["Description", "CustomerID", "Country"]


class DatasetImporter:
    """
    Parses, validates, normalizes, and ingests retail transaction files.
    """

    @staticmethod
    def detect_and_parse(file_bytes: bytes, filename: str) -> pd.DataFrame:
        """
        Parses raw bytes from CSV or Excel file into a pandas DataFrame.
        """
        fn = filename.lower().strip()
        bio = io.BytesIO(file_bytes)

        if fn.endswith(".xlsx") or fn.endswith(".xls"):
            try:
                df = pd.read_excel(bio, engine="openpyxl")
            except Exception:
                bio.seek(0)
                df = pd.read_excel(bio)
            return df

        # CSV / TSV / Text delimited handling
        # Try UTF-8 first, fallback to Latin-1 / ISO-8859-1
        try:
            content_str = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content_str = file_bytes.decode("latin-1")

        sio = io.StringIO(content_str)
        try:
            # Let pandas infer delimiter or default to comma
            df = pd.read_csv(sio, sep=None, engine="python")
        except Exception:
            sio.seek(0)
            df = pd.read_csv(sio, sep=",")

        return df

    @classmethod
    def match_columns(cls, raw_columns: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Maps raw input column headers to canonical names using alias matching.
        Returns (column_mapping, missing_required_columns).
        """
        normalized_inputs = {
            "".join(c.lower().replace("_", "").replace("-", "").replace(" ", "").split()): c
            for c in raw_columns
        }

        mapping: Dict[str, str] = {}
        for canonical, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                norm_alias = "".join(alias.lower().replace("_", "").replace("-", "").replace(" ", "").split())
                if norm_alias in normalized_inputs:
                    orig_col = normalized_inputs[norm_alias]
                    mapping[orig_col] = canonical
                    break

        missing_required = [col for col in REQUIRED_CANONICAL_COLUMNS if col not in mapping.values()]
        return mapping, missing_required

    @classmethod
    def validate_and_normalize(cls, df_raw: pd.DataFrame, filename: str = "upload.csv") -> Dict[str, Any]:
        """
        Validates schema, normalizes types, cleans records, and returns preview + telemetry.
        """
        if df_raw.empty:
            return {
                "valid": False,
                "filename": filename,
                "error": "The uploaded file is empty.",
                "total_rows_parsed": 0
            }

        mapping, missing_required = cls.match_columns(list(df_raw.columns))

        if missing_required:
            return {
                "valid": False,
                "filename": filename,
                "error": f"Missing required columns: {', '.join(missing_required)}.",
                "detected_mappings": mapping,
                "missing_required": missing_required,
                "input_columns": list(df_raw.columns),
                "total_rows_parsed": len(df_raw)
            }

        # Rename to canonical names
        df = df_raw.rename(columns=mapping).copy()

        # Fill optional columns if absent
        if "Description" not in df.columns:
            df["Description"] = "Generic Item"
        if "Country" not in df.columns:
            df["Country"] = "United Kingdom"
        if "CustomerID" not in df.columns:
            df["CustomerID"] = np.nan

        # Data cleaning and type conversions
        initial_row_count = len(df)
        df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
        df["StockCode"] = df["StockCode"].astype(str).str.strip()
        df["Description"] = df["Description"].fillna("Unknown Product").astype(str).str.strip()

        # Parse numeric columns
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
        df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")

        # Parse dates
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

        # Filter out invalid numeric/date rows
        valid_mask = (
            df["Quantity"].notna() &
            df["UnitPrice"].notna() &
            df["InvoiceDate"].notna() &
            (df["InvoiceNo"] != "") &
            (df["StockCode"] != "")
        )
        df_clean = df[valid_mask].copy()

        # Filter out cancellations and negative prices for clean commercial metrics
        df_clean["IsCancelled"] = df_clean["InvoiceNo"].str.startswith("C", na=False) | (df_clean["Quantity"] <= 0)
        valid_commercial = df_clean[~df_clean["IsCancelled"] & (df_clean["UnitPrice"] > 0)].copy()

        valid_commercial["TotalPrice"] = valid_commercial["Quantity"] * valid_commercial["UnitPrice"]

        # Date range string
        if not valid_commercial.empty:
            min_date = valid_commercial["InvoiceDate"].min().strftime("%Y-%m-%d")
            max_date = valid_commercial["InvoiceDate"].max().strftime("%Y-%m-%d")
            date_range_str = f"{min_date} to {max_date}"
            total_rev = float(np.round(valid_commercial["TotalPrice"].sum(), 2))
            total_units = int(valid_commercial["Quantity"].sum())
            unique_orders = int(valid_commercial["InvoiceNo"].nunique())
            unique_skus = int(valid_commercial["StockCode"].nunique())
            unique_customers = int(valid_commercial["CustomerID"].dropna().nunique())
        else:
            date_range_str = "N/A"
            total_rev = 0.0
            total_units = 0
            unique_orders = 0
            unique_skus = 0
            unique_customers = 0

        # Create top-5 preview records
        preview_sample = valid_commercial.head(5).copy() if not valid_commercial.empty else df.head(5).copy()
        if "InvoiceDate" in preview_sample.columns:
            preview_sample["InvoiceDate"] = preview_sample["InvoiceDate"].astype(str)

        preview_records = preview_sample.to_dict(orient="records")

        return {
            "valid": True,
            "filename": filename,
            "detected_mappings": mapping,
            "missing_required": [],
            "total_rows_parsed": initial_row_count,
            "valid_commercial_rows": len(valid_commercial),
            "cancelled_or_invalid_rows": initial_row_count - len(valid_commercial),
            "metrics": {
                "date_range": date_range_str,
                "total_revenue_gbp": total_rev,
                "total_units": total_units,
                "unique_orders": unique_orders,
                "unique_skus": unique_skus,
                "unique_customers": unique_customers,
                "average_order_value_gbp": float(np.round(total_rev / max(1, unique_orders), 2))
            },
            "preview_rows": preview_records
        }

    @classmethod
    def generate_sample_dataset(cls, num_rows: int = 15) -> pd.DataFrame:
        """
        Creates a realistic synthetic sample transactional dataset for templates.
        """
        sample_items = [
            ("22423", "REGENCY CAKESTAND 3 TIER", 12.75, "United Kingdom"),
            ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.95, "United Kingdom"),
            ("47566", "PARTY BUNTING", 4.95, "Germany"),
            ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69, "France"),
            ("20725", "LUNCH BAG RED RETROSPOT", 2.25, "United Kingdom"),
            ("22383", "LUNCH BAG SUKI DESIGN", 2.25, "United Kingdom"),
            ("22960", "JAM MAKING SET WITH JARS", 4.25, "Netherlands"),
            ("21212", "PACK OF 72 RETROSPOT CAKE CASES", 0.55, "United Kingdom"),
            ("85099B", "JUMBO BAG RED RETROSPOT", 2.08, "United Kingdom"),
            ("22720", "SET OF 3 CAKE TINS PANTRY DESIGN", 4.95, "Germany")
        ]

        customer_ids = [14096, 14911, 17841, 14646, 12415, 17511, 13089, 15311]

        data = []
        base_date = datetime(2026, 10, 15, 10, 30)

        for i in range(num_rows):
            item = sample_items[i % len(sample_items)]
            inv_no = f"58{1000 + (i // 2)}"
            qty = int(np.random.choice([6, 12, 24, 48, 100], p=[0.4, 0.3, 0.15, 0.1, 0.05]))
            cid = customer_ids[i % len(customer_ids)]
            order_date = base_date + pd.Timedelta(days=i // 3, hours=(i * 2) % 24)

            data.append({
                "InvoiceNo": inv_no,
                "StockCode": item[0],
                "Description": item[1],
                "Quantity": qty,
                "InvoiceDate": order_date.strftime("%Y-%m-%d %H:%M:%S"),
                "UnitPrice": item[2],
                "CustomerID": cid,
                "Country": item[3]
            })

        return pd.DataFrame(data)

    @classmethod
    def generate_template_bytes(cls, file_format: str = "csv") -> Tuple[bytes, str, str]:
        """
        Generates downloadable template file bytes, media_type, and filename.
        """
        df = cls.generate_sample_dataset(12)
        fmt = file_format.lower().strip()

        if fmt == "xlsx" or fmt == "excel":
            bio = io.BytesIO()
            with pd.ExcelWriter(bio, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Transactions")
            bio.seek(0)
            return (
                bio.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "nexus_retail_transactions_template.xlsx"
            )

        # Default CSV
        csv_str = df.to_csv(index=False)
        return (
            csv_str.encode("utf-8"),
            "text/csv",
            "nexus_retail_transactions_template.csv"
        )

    @classmethod
    def ingest_and_save_batch(cls, df_raw: pd.DataFrame, filename: str, merge_to_production: bool = True) -> Dict[str, Any]:
        """
        Saves uploaded batch to data/raw/imported_batches/ and appends clean records to processed parquet.
        """
        val_result = cls.validate_and_normalize(df_raw, filename)
        if not val_result["valid"]:
            return val_result

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = ROOT_DIR / "data" / "raw" / "imported_batches"
        batch_dir.mkdir(parents=True, exist_ok=True)

        batch_file = batch_dir / f"batch_{timestamp_str}_{filename.replace(' ', '_')}.parquet"
        
        mapping, _ = cls.match_columns(list(df_raw.columns))
        df_canonical = df_raw.rename(columns=mapping).copy()
        
        # Save raw batch parquet
        df_canonical.to_parquet(batch_file, index=False)

        prod_file = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"
        rows_added = 0

        if merge_to_production and prod_file.exists():
            prod_df = pd.read_parquet(prod_file)
            
            # Format canonical columns to align with production parquet schema
            clean_upload = df_canonical.copy()
            clean_upload["InvoiceNo"] = clean_upload["InvoiceNo"].astype(str)
            clean_upload["StockCode"] = clean_upload["StockCode"].astype(str)
            clean_upload["Description"] = clean_upload["Description"].fillna("Unknown Product").astype(str)
            clean_upload["Quantity"] = pd.to_numeric(clean_upload["Quantity"], errors="coerce").fillna(0).astype(int)
            clean_upload["UnitPrice"] = pd.to_numeric(clean_upload["UnitPrice"], errors="coerce").fillna(0.0).astype(float)
            clean_upload["InvoiceDate"] = pd.to_datetime(clean_upload["InvoiceDate"], errors="coerce")
            clean_upload["CustomerID"] = pd.to_numeric(clean_upload["CustomerID"], errors="coerce")
            clean_upload["Country"] = clean_upload.get("Country", "United Kingdom")
            clean_upload["IsCancelled"] = clean_upload["InvoiceNo"].str.startswith("C", na=False) | (clean_upload["Quantity"] <= 0)
            clean_upload["TotalPrice"] = clean_upload["Quantity"] * clean_upload["UnitPrice"]
            clean_upload["IsRegistered"] = clean_upload["CustomerID"].notna()

            # Align column order
            common_cols = [c for c in prod_df.columns if c in clean_upload.columns]
            merged_df = pd.concat([prod_df, clean_upload[common_cols]], ignore_index=True)
            merged_df.to_parquet(prod_file, index=False)
            rows_added = len(clean_upload)

        return {
            "valid": True,
            "filename": filename,
            "batch_file": str(batch_file.name),
            "merged_to_production": merge_to_production,
            "rows_added": rows_added,
            "metrics": val_result["metrics"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


if __name__ == "__main__":
    print("[Importer Engine] Generating sample dataset:")
    df_sample = DatasetImporter.generate_sample_dataset(5)
    print(df_sample.to_string())

    print("\n[Importer Engine] Testing validation:")
    val = DatasetImporter.validate_and_normalize(df_sample, "demo.csv")
    print(f"Valid: {val['valid']}, Metrics: {val['metrics']}")
