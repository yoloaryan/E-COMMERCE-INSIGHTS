"""
Exploratory Data Analysis (EDA) Engine for E-Commerce Intelligence.

Generates statistical profiles, revenue distributions, temporal purchase patterns,
country concentrations, and customer repeat behavior.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
FIGURES_DIR = Path(__file__).resolve().parents[2] / "data" / "figures"


class ECommerceEDA:
    """Computes critical business intelligence metrics and saves visual analytics."""

    def __init__(self, data_path: Path = None):
        if data_path is None:
            data_path = PROCESSED_DATA_DIR / "online_retail_cleaned.csv"
        self.data_path = data_path
        self.df: pd.DataFrame = None
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    def load_data(self) -> pd.DataFrame:
        print(f"[EDA] Loading processed data from {self.data_path}...")
        self.df = pd.read_csv(
            self.data_path,
            dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str},
            parse_dates=["InvoiceDate"]
        )
        return self.df

    def compute_executive_kpis(self) -> dict:
        """Returns fundamental business health metrics."""
        if self.df is None:
            self.load_data()

        valid_sales = self.df[(~self.df["IsCancelled"]) & (self.df["Quantity"] > 0)]

        total_revenue = valid_sales["TotalPrice"].sum()
        total_orders = valid_sales["InvoiceNo"].nunique()
        total_units = valid_sales["Quantity"].sum()
        aov = total_revenue / total_orders if total_orders > 0 else 0
        unique_customers = valid_sales["CustomerID"].dropna().nunique()
        unique_skus = valid_sales["StockCode"].nunique()

        kpis = {
            "Total Gross Revenue (£)": round(total_revenue, 2),
            "Total Completed Invoices": total_orders,
            "Total Units Sold": int(total_units),
            "Average Order Value (AOV £)": round(aov, 2),
            "Unique Registered Customers": unique_customers,
            "Unique Active SKUs": unique_skus,
            "Cancellation Rate (%)": round((self.df["IsCancelled"].sum() / len(self.df)) * 100, 2)
        }
        return kpis

    def get_top_selling_products(self, top_n: int = 10) -> pd.DataFrame:
        """Top products by revenue and quantity."""
        valid_sales = self.df[(~self.df["IsCancelled"]) & (self.df["Quantity"] > 0)]
        top_products = (
            valid_sales.groupby(["StockCode", "Description"])
            .agg(
                TotalQuantity=("Quantity", "sum"),
                TotalRevenue=("TotalPrice", "sum"),
                OrderCount=("InvoiceNo", "nunique")
            )
            .sort_values(by="TotalRevenue", ascending=False)
            .head(top_n)
            .reset_index()
        )
        return top_products

    def get_monthly_revenue_trend(self) -> pd.DataFrame:
        """Aggregates monthly gross sales."""
        valid_sales = self.df[(~self.df["IsCancelled"]) & (self.df["Quantity"] > 0)].copy()
        monthly = (
            valid_sales.groupby("YearMonth")
            .agg(
                MonthlyRevenue=("TotalPrice", "sum"),
                Orders=("InvoiceNo", "nunique"),
                Units=("Quantity", "sum")
            )
            .reset_index()
            .sort_values(by="YearMonth")
        )
        return monthly

    def get_country_breakdown(self, top_n: int = 10) -> pd.DataFrame:
        """Country-level market share."""
        valid_sales = self.df[(~self.df["IsCancelled"]) & (self.df["Quantity"] > 0)]
        country_df = (
            valid_sales.groupby("Country")
            .agg(
                Revenue=("TotalPrice", "sum"),
                Orders=("InvoiceNo", "nunique"),
                Customers=("CustomerID", "nunique")
            )
            .sort_values(by="Revenue", ascending=False)
            .reset_index()
        )
        country_df["RevenueShare (%)"] = round(
            (country_df["Revenue"] / country_df["Revenue"].sum()) * 100, 2
        )
        return country_df.head(top_n)


if __name__ == "__main__":
    eda = ECommerceEDA()
    eda.load_data()
    print("\n--- EXECUTIVE BUSINESS KPIS ---")
    for kpi, val in eda.compute_executive_kpis().items():
        print(f"  {kpi}: {val:,}" if isinstance(val, (int, float)) else f"  {kpi}: {val}")
    
    print("\n--- TOP 5 PRODUCTS BY REVENUE ---")
    print(eda.get_top_selling_products(5))

    print("\n--- TOP 5 COUNTRIES BY REVENUE ---")
    print(eda.get_country_breakdown(5))
