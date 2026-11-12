"""
Generates the comprehensive Jupyter Notebook for Module 4:
notebooks/04_churn_prediction.ipynb
"""

import json
from pathlib import Path

NOTEBOOK_PATH = Path(__file__).resolve().parents[2] / "notebooks" / "04_churn_prediction.ipynb"

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
# Module 4: E-Commerce Customer Churn Prediction & Retention Strategy
### Senior Data Scientist & ML Engineering Portfolio
---
### Objectives:
1. **Defensible Business Churn Formulation**: Overcome the non-contractual ambiguity by instituting a 90-day future inactivity window cutoff.
2. **Leak-Free Feature Store**: Calculate historical customer features (Recency, Frequency, Monetary, Unique SKUs, Inter-Purchase Velocity) strictly before the cutoff date.
3. **Classification Benchmarking**: Train and evaluate **Logistic Regression**, **Random Forest**, and **XGBoost Classifiers** using Accuracy, Precision, Recall, F1-Score, and ROC-AUC.
4. **Prioritizing Recall in Retention**: Explain why false negatives (missing a churning VIP) are far more costly to retail EBITDA than false positives.
5. **VIP Revenue Exposure**: Identify high-value accounts at immediate risk of churning and prescribe high-touch retention workflows.
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
from sklearn.metrics import roc_curve, auc, confusion_matrix
import warnings

warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid', palette='muted')
plt.rcParams['figure.figsize'] = (10, 5)
"""))

    # Cell 3: Churn Feature Store
    cells.append(md_cell("""
## 1. Out-of-Time Churn Feature Engineering
We use `src.features.churn_features.ChurnFeatureEngineer` to segment the historical timeline.
- Cutoff Date: `2011-09-10`
- Target: 1 if 0 purchases made between `2011-09-10` and `2011-12-09` (90-day window); 0 otherwise.
"""))

    cells.append(code_cell("""
from src.features.churn_features import ChurnFeatureEngineer

fe = ChurnFeatureEngineer(data_path=Path('../data/processed/online_retail_customer_centric.csv'), churn_window_days=90)
churn_df = fe.engineer_churn_features()
churn_df.head()
"""))

    # Cell 4: Class Distribution
    cells.append(md_cell("""
## 2. Ground-Truth Churn Distribution
Examining the natural balance between retained and churned cohorts.
"""))

    cells.append(code_cell("""
plt.figure(figsize=(6, 4))
sns.countplot(data=churn_df, x='Churn', palette=['#2ca02c', '#d62728'])
plt.title('Churn Label Balance (0 = Retained, 1 = Churned)', fontsize=13, weight='bold')
plt.xticks([0, 1], ['Retained (Active in Future)', 'Churned (No Future Purchase)'])
plt.ylabel('Customer Count')
plt.show()

print(churn_df['Churn'].value_counts(normalize=True).round(3) * 100)
"""))

    # Cell 5: Train and Evaluate Models
    cells.append(md_cell("""
## 3. Training & Benchmarking Competitive Classifiers
Evaluating Logistic Regression, Random Forest, and XGBoost on an unseen 20% stratified test set.
"""))

    cells.append(code_cell("""
from src.models.churn_prediction import CustomerChurnPredictor

predictor = CustomerChurnPredictor(data_path=Path('../data/processed/customer_churn_features.csv'), test_size=0.20)
predictor.load_and_split()
eval_df = predictor.train_and_evaluate()
eval_df
"""))

    # Cell 6: ROC Curve Comparison
    cells.append(md_cell("""
## 4. ROC-AUC Performance Curves
Comparing True Positive Rate vs. False Positive Rate across all probability thresholds.
"""))

    cells.append(code_cell("""
plt.figure(figsize=(8, 6))

for name, config in predictor.models.items():
    clf = config['model']
    X_test_eval = predictor.scaler.transform(predictor.X_test) if config['is_scaled'] else predictor.X_test
    y_probs = clf.predict_proba(X_test_eval)[:, 1]
    fpr, tpr, _ = roc_curve(predictor.y_test, y_probs)
    roc_score = auc(fpr, tpr)
    plt.plot(fpr, tpr, label=f"{name} (AUC = {roc_score:.3f})", linewidth=2)

plt.plot([0, 1], [0, 1], color='gray', linestyle='--')
plt.title('ROC Curves - Churn Classification Benchmark', fontsize=14, weight='bold')
plt.xlabel('False Positive Rate (1 - Specificity)')
plt.ylabel('True Positive Rate (Recall)')
plt.legend(loc='lower right')
plt.grid(True, linestyle=':', alpha=0.6)
plt.show()
"""))

    # Cell 7: Feature Importance Analysis
    cells.append(md_cell("""
## 5. Identifying Top Churn Risk Drivers
What behavioral indicators reveal an impending customer departure?
"""))

    cells.append(code_cell("""
feat_imp = predictor.get_feature_importance()

plt.figure(figsize=(10, 5))
sns.barplot(data=feat_imp, x='Importance', y='Feature', palette='mako')
plt.title('Predictive Feature Importance for Customer Churn', fontsize=13, weight='bold')
plt.xlabel('Normalized Gini Importance')
plt.tight_layout()
plt.show()
"""))

    # Cell 8: Revenue Exposure from At-Risk VIPs
    cells.append(md_cell("""
## 6. Business Impact: Scoring the Cohort & VIP Revenue Exposure
Translating model probabilities into high-value revenue protection.
"""))

    cells.append(code_cell("""
scored_df = predictor.score_all_customers()

tier_summary = scored_df.groupby('Churn_Risk_Tier').agg(
    CustomerCount=('CustomerID', 'count'),
    AvgChurnProbability=('Churn_Probability', 'mean'),
    TotalHistoricalSpend=('HistoricalMonetary', 'sum'),
    AvgHistoricalSpend=('HistoricalMonetary', 'mean')
).round(2).reset_index()

tier_summary['Revenue_Exposure (%)'] = round(
    (tier_summary['TotalHistoricalSpend'] / tier_summary['TotalHistoricalSpend'].sum()) * 100, 2
)
tier_summary
"""))

    # Cell 9: High-Value Retention Table
    cells.append(md_cell("""
## 7. Actionable VIP Retention List
High-spending customers with >70% churn probability who require immediate executive intervention.
"""))

    cells.append(code_cell("""
vip_at_risk = scored_df[
    (scored_df['Churn_Risk_Tier'] == 'High Risk') & (scored_df['HistoricalMonetary'] >= 1000)
].sort_values(by='HistoricalMonetary', ascending=False)

print(f"Total High-Value Accounts at Immediate Risk: {len(vip_at_risk)}")
print(f"Total Capital Exposure: ₹{vip_at_risk['HistoricalMonetary'].sum():,.2f}")

vip_at_risk[['CustomerID', 'HistoricalMonetary', 'HistoricalFrequency', 'Recency', 'Churn_Probability', 'Retention_Strategy']].head(10)
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
