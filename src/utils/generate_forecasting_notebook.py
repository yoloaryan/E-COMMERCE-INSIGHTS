"""
Generates the comprehensive Jupyter Notebook for Module 3:
notebooks/03_sales_prediction.ipynb
"""

import json
from pathlib import Path

NOTEBOOK_PATH = Path("/Users/aryangupta/Desktop/e-commerce/notebooks/03_sales_prediction.ipynb")

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

    # Cell 1: Header
    cells.append(md_cell("""
# Module 3: E-Commerce Sales Prediction & Demand Forecasting
### Senior Data Scientist & ML Engineering Portfolio
---
### Objectives:
1. **Time-Series Aggregation**: Formulate continuous daily gross sales across 374 operating days.
2. **Feature Engineering**: Construct autoregressive lags (`Lag_1`, `Lag_7`, `Lag_14`), rolling window momentum, and calendar signals.
3. **Temporal Validation**: Implement chronological train/test splitting (80% historical train, 20% future test) to prevent lookahead data leakage.
4. **Model Benchmarking**: Compare **Linear Regression**, **Random Forest**, and **XGBoost Regressor** using MAE, RMSE, MAPE, and $R^2$.
5. **Feature Importance & Business Translation**: Connect weekly seasonal demand signals to supply chain stockout prevention.
"""))

    # Cell 2: Imports
    cells.append(code_cell("""
import sys
from pathlib import Path
sys.path.append('..')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.figsize'] = (12, 5)
"""))

    # Cell 3: Feature Engineering
    cells.append(md_cell("""
## 1. Constructing Time-Series Predictors
We utilize `src.features.sales_features.SalesFeatureEngineer` to generate autoregressive and rolling features.
"""))

    cells.append(code_cell("""
from src.features.sales_features import SalesFeatureEngineer

fe = SalesFeatureEngineer(data_path=Path('../data/processed/online_retail_cleaned.csv'))
daily_df = fe.engineer_time_series_features()
daily_df[['Date', 'DailyRevenue', 'Lag_1', 'Lag_7', 'RollingMean_7', 'DayOfWeek', 'Month']].head()
"""))

    # Cell 4: Visualizing Sales Trends & Seasonality
    cells.append(md_cell("""
## 2. Historical Daily Revenue & Day-of-Week Seasonality
Inspecting daily volatility and weekly cyclicality in transaction volumes.
"""))

    cells.append(code_cell("""
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5))

# Daily trajectory
ax1.plot(daily_df['Date'], daily_df['DailyRevenue'], color='#1f77b4', linewidth=1.5)
ax1.plot(daily_df['Date'], daily_df['RollingMean_7'], color='#ff7f0e', linewidth=2.5, label='7-Day Moving Avg')
ax1.set_title('Daily Gross Revenue Trajectory (£)', fontsize=13, weight='bold')
ax1.set_ylabel('Revenue (£)')
ax1.legend()

# Day of week pattern
day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
sns.barplot(data=daily_df, x='DayOfWeek', y='DailyRevenue', ax=ax2, palette='Blues_d')
ax2.set_xticklabels(day_labels)
ax2.set_title('Average Daily Revenue by Day of Week', fontsize=13, weight='bold')
ax2.set_ylabel('Avg Revenue (£)')

plt.tight_layout()
plt.show()
"""))

    # Cell 5: Chronological Training & Evaluation
    cells.append(md_cell("""
## 3. Strict Chronological Split & Competitive Model Training
We benchmark **Linear Regression**, **Random Forest**, and **XGBoost** on an unseen 69-day test horizon (Oct 2011 - Dec 2011).
"""))

    cells.append(code_cell("""
from src.models.sales_forecasting import SalesForecastingPipeline

pipeline = SalesForecastingPipeline(data_path=Path('../data/processed/daily_sales_features.csv'), test_size=0.20)
pipeline.load_and_split()
eval_df = pipeline.train_and_evaluate()
eval_df
"""))

    # Cell 6: Visualizing Forecast vs Actuals
    cells.append(md_cell("""
## 4. Out-of-Sample Forecast Tracking vs. Actual Sales
Comparing the best performing model's predictions against ground-truth receipts.
"""))

    cells.append(code_cell("""
preds_df = pd.read_csv('../data/processed/sales_forecast_results.csv', parse_dates=['Date'])

plt.figure(figsize=(14, 6))
plt.plot(preds_df['Date'], preds_df['ActualRevenue'], label='Actual Sales (£)', color='black', linewidth=2, marker='o', markersize=4)
plt.plot(preds_df['Date'], preds_df['Pred_Random Forest Regressor'], label='Random Forest Forecast', color='#2ca02c', linewidth=2.5, linestyle='--')
plt.plot(preds_df['Date'], preds_df['Pred_XGBoost Regressor'], label='XGBoost Forecast', color='#1f77b4', linewidth=2, linestyle=':')
plt.title('Out-of-Sample Sales Forecast Comparison (Q4 Peak)', fontsize=14, weight='bold')
plt.xlabel('Date')
plt.ylabel('Daily Gross Revenue (£)')
plt.legend(fontsize=11)
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()
"""))

    # Cell 7: Feature Importance & Interpretability
    cells.append(md_cell("""
## 5. Model Interpretability & Business Decision Making
Which features contribute most strongly to sales predictions?
"""))

    cells.append(code_cell("""
feat_imp = pipeline.get_feature_importance().head(10)

plt.figure(figsize=(10, 5))
sns.barplot(data=feat_imp, x='Importance', y='Feature', palette='crest')
plt.title('Top 10 Feature Importances (Random Forest)', fontsize=13, weight='bold')
plt.xlabel('Normalized Gini Importance')
plt.tight_layout()
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
