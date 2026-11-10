"""
Automated Pipeline Data Export Engine.

Extracts real, audited aggregations and predictions from processed Parquet files
and serialized ML models, generating a clean `data/nexus_data.json` bundle for
client-side dashboard consumption.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

import json
import joblib
import pandas as pd
import duckdb

DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"
OUTPUT_JSON_PATH = ROOT_DIR / "data" / "nexus_data.json"


def export_dashboard_data():
    print(f"[Export] Generating production web dataset from {DATA_PROCESSED_DIR}...")

    # 1. Connect DuckDB over cleaned parquet
    pq_store = DATA_PROCESSED_DIR / "online_retail_cleaned.parquet"
    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE VIEW transactions AS SELECT * FROM read_parquet('{pq_store}');")

    # Macro KPIs
    kpi_res = con.execute("""
        SELECT 
            ROUND(SUM(TotalPrice), 2) AS total_revenue,
            COUNT(DISTINCT InvoiceNo) AS total_orders,
            SUM(Quantity) AS total_units,
            COUNT(DISTINCT CustomerID) AS registered_customers,
            COUNT(DISTINCT StockCode) AS active_skus,
            ROUND((SUM(CASE WHEN IsCancelled THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 2) AS cancel_rate
        FROM transactions
        WHERE IsCancelled = FALSE AND Quantity > 0;
    """).df().iloc[0]

    # Top Products
    top_products_df = con.execute("""
        SELECT 
            StockCode AS stock_code,
            FIRST(Description) AS description,
            ROUND(SUM(TotalPrice), 2) AS revenue,
            SUM(Quantity) AS units_sold,
            COUNT(DISTINCT InvoiceNo) AS order_count
        FROM transactions
        WHERE IsCancelled = FALSE AND Quantity > 0
        GROUP BY StockCode
        ORDER BY revenue DESC
        LIMIT 10;
    """).df()

    # Monthly Trends
    monthly_df = con.execute("""
        SELECT 
            strftime(InvoiceDate, '%Y-%m') AS month,
            ROUND(SUM(TotalPrice), 2) AS revenue,
            COUNT(DISTINCT InvoiceNo) AS orders
        FROM transactions
        WHERE IsCancelled = FALSE AND Quantity > 0
        GROUP BY month
        ORDER BY month ASC;
    """).df()

    # 2. Segments Data
    segments_path = DATA_PROCESSED_DIR / "customer_segments.parquet"
    seg_df = pd.read_parquet(segments_path)
    seg_summary = (
        seg_df.groupby("Segment_Name")
        .agg(
            customer_count=("CustomerID", "count"),
            avg_recency=("Recency", "mean"),
            avg_frequency=("Frequency", "mean"),
            avg_monetary=("Monetary", "mean"),
            total_revenue=("Monetary", "sum")
        )
        .reset_index()
    )
    total_seg_rev = seg_summary["total_revenue"].sum()
    seg_summary["revenue_share_pct"] = (seg_summary["total_revenue"] / total_seg_rev * 100).round(2)
    seg_summary["avg_recency"] = seg_summary["avg_recency"].round(1)
    seg_summary["avg_frequency"] = seg_summary["avg_frequency"].round(1)
    seg_summary["avg_monetary"] = seg_summary["avg_monetary"].round(2)

    # 3. Churn Early Warning VIPs
    churn_path = DATA_PROCESSED_DIR / "customer_churn_predictions.parquet"
    churn_df = pd.read_parquet(churn_path)
    at_risk_vips = churn_df[
        (churn_df["Churn_Risk_Tier"] == "High Risk") &
        (churn_df["HistoricalMonetary"] >= 1000)
    ].sort_values(by="HistoricalMonetary", ascending=False).head(20)

    # 4. Sales Forecast Timeline
    forecast_path = DATA_PROCESSED_DIR / "sales_forecast_results.parquet"
    forecast_df = pd.read_parquet(forecast_path)
    forecast_timeline = [
        {
            "date": str(row["Date"])[:10],
            "actual": round(float(row["ActualRevenue"]), 2),
            "rf_predicted": round(float(row["Pred_Random Forest Regressor"]), 2),
            "xgb_predicted": round(float(row["Pred_XGBoost Regressor"]), 2),
            "p10_lower": round(float(row["P10_Lower_Bound"]), 2) if "P10_Lower_Bound" in row else 0.0,
            "p90_upper": round(float(row["P90_Upper_Bound"]), 2) if "P90_Upper_Bound" in row else 0.0
        }
        for _, row in forecast_df.iterrows()
    ]

    # 5. Product Catalog Sample
    cat_path = MODELS_DIR / "product_catalog.joblib"
    catalog = joblib.load(cat_path) if cat_path.exists() else {}
    sample_catalog = [
        {"stock_code": k, "description": v["Description"], "unit_price": v["UnitPrice"], "orders": v["TotalOrders"]}
        for k, v in list(catalog.items())[:50]
    ]

    payload = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "kpis": {
            "total_gross_revenue_gbp": round(float(kpi_res["total_revenue"]), 2),
            "total_completed_orders": int(kpi_res["total_orders"]),
            "total_units_sold": int(kpi_res["total_units"]),
            "average_order_value_gbp": round(float(kpi_res["total_revenue"] / kpi_res["total_orders"]), 2),
            "registered_customers": int(kpi_res["registered_customers"]),
            "active_catalog_skus": int(kpi_res["active_skus"]),
            "cancellation_rate_pct": float(kpi_res["cancel_rate"])
        },
        "monthly_velocity": monthly_df.to_dict(orient="records"),
        "top_products": top_products_df.to_dict(orient="records"),
        "segments": seg_summary.to_dict(orient="records"),
        "at_risk_vips": [
            {
                "customer_id": str(row["CustomerID"]),
                "historical_spend": round(float(row["HistoricalMonetary"]), 2),
                "churn_probability": round(float(row["Churn_Probability"]), 3),
                "recency_days": int(row["Recency"]),
                "lifetime_orders": int(row["HistoricalFrequency"]),
                "retention_strategy": row["Retention_Strategy"]
            }
            for _, row in at_risk_vips.iterrows()
        ],
        "forecast_timeline": forecast_timeline,
        "sample_catalog": sample_catalog
    }

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(payload, f, indent=2)

    size_kb = OUTPUT_JSON_PATH.stat().st_size / 1024
    print(f"[Export] Successfully generated {OUTPUT_JSON_PATH} ({size_kb:.1f} KB).")
    return payload


if __name__ == "__main__":
    export_dashboard_data()

