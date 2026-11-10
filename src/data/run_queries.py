"""
In-Process SQL Analytics Engine using DuckDB.

Executes enterprise analytical queries from sql/schema_and_queries.sql directly
against compressed Parquet datasets without requiring an external MySQL server.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import duckdb
import pandas as pd

PARQUET_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.parquet"
CSV_PATH = ROOT_DIR / "data" / "processed" / "online_retail_cleaned.csv"


class DuckDBAnalyticsRunner:
    """Runs SQL analytics mart queries against local parquet / csv files."""

    def __init__(self, data_path: Path = None):
        if data_path is None:
            data_path = PARQUET_PATH if PARQUET_PATH.exists() else CSV_PATH
        self.data_path = data_path
        self.con = duckdb.connect(database=":memory:")
        self._setup_view()

    def _setup_view(self):
        """Creates standard SQL view named 'ecommerce_transactions' over dataset."""
        print(f"[DuckDB] Initializing in-memory analytics mart from: {self.data_path}")
        if str(self.data_path).endswith(".parquet"):
            self.con.execute(f"""
                CREATE OR REPLACE VIEW ecommerce_transactions AS 
                SELECT 
                    InvoiceNo AS invoice_no,
                    StockCode AS stock_code,
                    Description AS description,
                    Quantity AS quantity,
                    InvoiceDate AS invoice_date,
                    UnitPrice AS unit_price,
                    CustomerID AS customer_id,
                    Country AS country,
                    IsCancelled AS is_cancelled,
                    IsGuest AS is_guest,
                    TotalPrice AS total_price
                FROM read_parquet('{self.data_path}');
            """)
        else:
            self.con.execute(f"""
                CREATE OR REPLACE VIEW ecommerce_transactions AS 
                SELECT 
                    InvoiceNo AS invoice_no,
                    StockCode AS stock_code,
                    Description AS description,
                    Quantity AS quantity,
                    InvoiceDate AS invoice_date,
                    UnitPrice AS unit_price,
                    CustomerID AS customer_id,
                    Country AS country,
                    IsCancelled AS is_cancelled,
                    IsGuest AS is_guest,
                    TotalPrice AS total_price
                FROM read_csv_auto('{self.data_path}');
            """)

    def query_monthly_velocity(self) -> pd.DataFrame:
        """Query 1: Monthly Sales Velocity & Average Order Value (AOV)."""
        sql = """
        SELECT 
            strftime(invoice_date, '%Y-%m') AS sales_month,
            COUNT(DISTINCT invoice_no) AS total_orders,
            SUM(quantity) AS total_units_sold,
            ROUND(SUM(total_price), 2) AS gross_revenue,
            ROUND(SUM(total_price) / COUNT(DISTINCT invoice_no), 2) AS average_order_value
        FROM ecommerce_transactions
        WHERE is_cancelled = FALSE 
          AND quantity > 0 
          AND unit_price > 0
        GROUP BY sales_month
        ORDER BY sales_month ASC;
        """
        return self.con.execute(sql).df()

    def query_top_products(self, top_n: int = 10) -> pd.DataFrame:
        """Query 2: Top Products by Revenue & Units Sold."""
        sql = f"""
        SELECT 
            stock_code,
            FIRST(description) AS description,
            SUM(quantity) AS total_units_sold,
            ROUND(SUM(total_price), 2) AS gross_revenue,
            COUNT(DISTINCT invoice_no) AS order_frequency
        FROM ecommerce_transactions
        WHERE is_cancelled = FALSE 
          AND quantity > 0
        GROUP BY stock_code
        ORDER BY gross_revenue DESC
        LIMIT {top_n};
        """
        return self.con.execute(sql).df()

    def query_rfm_summary(self, top_n: int = 10) -> pd.DataFrame:
        """Query 3: SQL-based RFM Aggregations."""
        sql = f"""
        WITH reference_table AS (
            SELECT MAX(invoice_date) + INTERVAL 1 DAY AS ref_date
            FROM ecommerce_transactions
        )
        SELECT 
            customer_id,
            DATE_DIFF('day', MAX(invoice_date), (SELECT ref_date FROM reference_table)) AS recency_days,
            COUNT(DISTINCT invoice_no) AS frequency_orders,
            ROUND(SUM(total_price), 2) AS monetary_value,
            MIN(invoice_date) AS first_purchase_date,
            MAX(invoice_date) AS last_purchase_date
        FROM ecommerce_transactions
        WHERE customer_id IS NOT NULL 
          AND is_cancelled = FALSE 
          AND quantity > 0
        GROUP BY customer_id
        ORDER BY monetary_value DESC
        LIMIT {top_n};
        """
        return self.con.execute(sql).df()

    def query_churn_inactivity_audit(self) -> pd.DataFrame:
        """Query 4: Customer Inactivity / Churn Rule Audit (>90 Days Inactive)."""
        sql = """
        WITH customer_last_purchase AS (
            SELECT 
                customer_id,
                MAX(invoice_date) AS last_purchase_date,
                COUNT(DISTINCT invoice_no) AS lifetime_orders,
                SUM(total_price) AS lifetime_spend
            FROM ecommerce_transactions
            WHERE customer_id IS NOT NULL 
              AND is_cancelled = FALSE 
              AND quantity > 0
            GROUP BY customer_id
        ),
        reference_info AS (
            SELECT MAX(invoice_date) AS max_date FROM ecommerce_transactions
        ),
        churn_evaluated AS (
            SELECT 
                customer_id,
                last_purchase_date,
                lifetime_orders,
                lifetime_spend,
                DATE_DIFF('day', last_purchase_date, (SELECT max_date FROM reference_info)) AS days_since_last_purchase,
                CASE 
                    WHEN DATE_DIFF('day', last_purchase_date, (SELECT max_date FROM reference_info)) > 90 THEN 1 
                    ELSE 0 
                END AS is_churned
            FROM customer_last_purchase
        )
        SELECT 
            is_churned,
            COUNT(customer_id) AS total_customers,
            ROUND(COUNT(customer_id) * 100.0 / (SELECT COUNT(*) FROM churn_evaluated), 2) AS customer_percentage,
            ROUND(AVG(lifetime_spend), 2) AS avg_historical_spend,
            ROUND(AVG(lifetime_orders), 1) AS avg_orders
        FROM churn_evaluated
        GROUP BY is_churned
        ORDER BY is_churned ASC;
        """
        return self.con.execute(sql).df()

    def run_all(self):
        """Runs and displays all analytical SQL queries."""
        print("\n" + "="*80)
        print("QUERY 1: Monthly Sales Velocity & Average Order Value (AOV)")
        print("="*80)
        print(self.query_monthly_velocity().to_string(index=False))

        print("\n" + "="*80)
        print("QUERY 2: Top 10 High-Velocity Products (Gross Revenue & Units)")
        print("="*80)
        print(self.query_top_products(10).to_string(index=False))

        print("\n" + "="*80)
        print("QUERY 3: RFM Raw Feature Aggregation (Top 10 Spenders)")
        print("="*80)
        print(self.query_rfm_summary(10).to_string(index=False))

        print("\n" + "="*80)
        print("QUERY 4: Customer Inactivity / Churn Rule Audit (>90 Days)")
        print("="*80)
        print(self.query_churn_inactivity_audit().to_string(index=False))


if __name__ == "__main__":
    runner = DuckDBAnalyticsRunner()
    runner.run_all()

