"""
Generates the professional Jupyter Notebook for Phase 2:
notebooks/01_data_cleaning_eda.ipynb
"""

import json
from pathlib import Path

NOTEBOOK_PATH = Path(__file__).resolve().parents[2] / "notebooks" / "01_data_cleaning_eda.ipynb"

def build_notebook():
    cells = []

    def md_cell(text):
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in text.strip().split("\n")]
        }

    def code_cell(code):
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in code.strip().split("\n")]
        }

    # Cell 1: Title
    cells.append(md_cell("""
# Module 1: E-Commerce Data Cleaning, Preprocessing & Deep EDA
### Author: Senior Data Scientist & ML Engineer Portfolio
---
### Objectives:
1. **Data Ingestion**: Load the UCI Online Retail dataset (541k+ transactional rows).
2. **Data Cleaning & Auditing**: Handle missing values, filter non-product records, and separate cancellations.
3. **Dual Dataset Architecture**:
   - Store-level cleaned dataset (for aggregate macro sales forecasting).
   - Customer-centric dataset (for RFM, churn, and collaborative filtering).
4. **Exploratory Data Analysis (EDA)**: Executive KPIs, Pareto principle in product revenues, temporal purchase rhythms, and country concentration.
"""))

    # Cell 2: Imports
    cells.append(code_cell("""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import warnings

warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 11

print("Environment libraries successfully loaded.")
"""))

    # Cell 3: Data Ingestion
    cells.append(md_cell("""
## 1. Data Ingestion & Schema Inspection
We load the preprocessed CSV version of the raw dataset. Each row is an invoice item representing an individual purchase transaction.
"""))

    cells.append(code_cell("""
# Load raw dataset
data_path = Path('../data/raw/online_retail.csv')
if not data_path.exists():
    raise FileNotFoundError("Raw CSV not found. Please run src/data/ingest.py first.")

df_raw = pd.read_csv(
    data_path,
    dtype={'InvoiceNo': str, 'StockCode': str, 'CustomerID': str},
    parse_dates=['InvoiceDate']
)

print(f"Total Raw Records: {len(df_raw):,}")
print(f"Total Features: {df_raw.shape[1]}")
df_raw.head()
"""))

    # Cell 4: Missing Value Analysis
    cells.append(md_cell("""
## 2. Missing Value & Anomaly Diagnostics
Real transactional data contains critical gaps. We analyze null counts and assess business reasons behind missing customer identifiers (Guest Checkouts).
"""))

    cells.append(code_cell("""
missing_summary = pd.DataFrame({
    'Missing_Count': df_raw.isnull().sum(),
    'Percentage (%)': (df_raw.isnull().sum() / len(df_raw) * 100).round(2)
})
missing_summary[missing_summary['Missing_Count'] > 0]
"""))

    # Cell 5: Cancellations and Invalid Quantities
    cells.append(md_cell("""
## 3. Handling Cancellations & Negative Quantities
In the UK Online Retail dataset, invoice numbers prefixed with **'C'** denote customer cancellations or returns.
These rows typically carry negative quantities.
"""))

    cells.append(code_cell("""
cancellations = df_raw[df_raw['InvoiceNo'].str.startswith('C', na=False) | (df_raw['Quantity'] < 0)]
print(f"Total Cancellation / Return Records: {len(cancellations):,} ({len(cancellations)/len(df_raw)*100:.2f}%)")
cancellations.head(3)
"""))

    # Cell 6: Run Cleaning Engine
    cells.append(md_cell("""
## 4. Pipeline Execution: Creating Dual-Cleaned Datasets
We invoke our production cleaner from `src.data.clean.ECommerceDataCleaner` to produce:
1. `online_retail_cleaned.csv`: Validated store transactions.
2. `online_retail_customer_centric.csv`: Confirmed customer-identified transactions.
"""))

    cells.append(code_cell("""
import sys
sys.path.append('..')
from src.data.clean import ECommerceDataCleaner

cleaner = ECommerceDataCleaner(raw_csv_path=Path('../data/raw/online_retail.csv'))
cleaner.clean_transactions()
audit = cleaner.generate_audit_summary()

for metric, val in audit.items():
    print(f"{metric:25s}: {val}")
"""))

    # Cell 7: Executive KPIs
    cells.append(md_cell("""
## 5. Executive Business KPIs
High-level operational health indicators derived from clean transactional records.
"""))

    cells.append(code_cell("""
from src.data.eda import ECommerceEDA

eda = ECommerceEDA(data_path=Path('../data/processed/online_retail_cleaned.csv'))
kpis = eda.compute_executive_kpis()

pd.DataFrame(list(kpis.items()), columns=['Business KPI', 'Value'])
"""))

    # Cell 8: Top 10 Products by Revenue
    cells.append(md_cell("""
## 6. Product Performance & Pareto Principle (80/20 Rule)
Which top products drive the greatest revenue and volume?
"""))

    cells.append(code_cell("""
top_products = eda.get_top_selling_products(10)
plt.figure(figsize=(10, 5))
sns.barplot(data=top_products, x='TotalRevenue', y='Description', palette='viridis')
plt.title('Top 10 Products by Gross Revenue (₹)', fontsize=14, weight='bold')
plt.xlabel('Gross Revenue (₹)')
plt.ylabel('Product Description')
plt.tight_layout()
plt.show()
"""))

    # Cell 9: Monthly Sales Velocity
    cells.append(md_cell("""
## 7. Temporal Sales Trends & Seasonality
Analyzing monthly revenue trajectories to identify Q4 holiday shopping peaks.
"""))

    cells.append(code_cell("""
monthly_sales = eda.get_monthly_revenue_trend()
plt.figure(figsize=(12, 5))
plt.plot(monthly_sales['YearMonth'], monthly_sales['MonthlyRevenue'], marker='o', linewidth=2.5, color='#2b5c8f')
plt.fill_between(range(len(monthly_sales)), monthly_sales['MonthlyRevenue'], color='#2b5c8f', alpha=0.15)
plt.title('Monthly Gross Revenue Trajectory (Nov 2010 - Dec 2011)', fontsize=14, weight='bold')
plt.xlabel('Year-Month')
plt.ylabel('Gross Revenue (₹)')
plt.xticks(rotation=45)
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()
"""))

    # Cell 10: Geographic Breakdown
    cells.append(md_cell("""
## 8. Geographic Revenue Concentration
Examining domestic (UK) vs international market distribution.
"""))

    cells.append(code_cell("""
country_share = eda.get_country_breakdown(8)
plt.figure(figsize=(8, 8))
plt.pie(country_share['Revenue'], labels=country_share['Country'], autopct='%1.1f%%', startangle=140, colors=sns.color_palette('pastel'))
plt.title('Geographic Revenue Distribution (Top Markets)', fontsize=14, weight='bold')
plt.show()
"""))

    nb_json = {
        "cells": cells,
        "metadata": {
            "language_info": {"name": "python", "version": "3.11"},
            "kernelspec": {"display_name": "Python 3.11", "language": "python", "name": "python3"}
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb_json, f, indent=2)
    print(f"Jupyter Notebook successfully created at {NOTEBOOK_PATH}")

if __name__ == "__main__":
    build_notebook()
