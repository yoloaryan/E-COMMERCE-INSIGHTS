"""
Generates the comprehensive Jupyter Notebook for Module 5:
notebooks/05_product_recommendation.ipynb
"""

import json
from pathlib import Path

NOTEBOOK_PATH = Path(__file__).resolve().parents[2] / "notebooks" / "05_product_recommendation.ipynb"

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
# Module 5: E-Commerce Product Recommendation System
### Item-Based Collaborative Filtering & Cosine Similarity
### Senior Data Scientist & ML Engineering Portfolio
---
### Objectives:
1. **Interaction Matrix**: Construct high-dimensional customer-product interaction matrices from 395k+ clean transactional lines.
2. **Mathematical Intuition of Item-Based Collaborative Filtering**:
   $$\\text{Cosine Similarity}(i, j) = \\frac{\\mathbf{u}_i \\cdot \\mathbf{u}_j}{\\|\\mathbf{u}_i\\|_2 \\|\\mathbf{u}_j\\|_2}$$
3. **Item-to-Item Cross-Selling**: Implement "Frequently Bought Together" recommendations for catalog product detail pages.
4. **Personalized User Recommendations**: Aggregate affinity vectors across a customer's lifetime purchase history and filter out already-purchased SKUs.
5. **Cold-Start Handling**: Implement high-velocity bestseller fallback for new visitors.
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
import warnings

warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid', palette='muted')
"""))

    # Cell 3: Initialize Recommender
    cells.append(md_cell("""
## 1. Initializing the Recommender Engine
We invoke `src.models.recommender.ProductRecommender` to load verified customer transactions and construct the catalog.
"""))

    cells.append(code_cell("""
from src.models.recommender import ProductRecommender

recommender = ProductRecommender(data_path=Path('../data/processed/online_retail_customer_centric.csv'), min_interactions=5)
recommender.load_and_preprocess()
recommender.build_similarity_matrix()
print(f"Similarity matrix shape: {recommender.similarity_df.shape}")
"""))

    # Cell 4: Item-to-Item Cross Sell
    cells.append(md_cell("""
## 2. Item-to-Item Cross-Sell ("Frequently Bought Together")
When a customer views the **Regency Cakestand 3 Tier (StockCode: 22423)**, what complementary items should we showcase on the product page?
"""))

    cells.append(code_cell("""
sample_sku = "22423"
meta = recommender.product_catalog[sample_sku]
print(f"Base Product: [{sample_sku}] {meta['Description']} (₹{meta['UnitPrice']})")

similar_items = recommender.recommend_similar_items(sample_sku, top_n=5)
pd.DataFrame(similar_items)
"""))

    # Cell 5: Visualizing Similarity Heatmap
    cells.append(md_cell("""
## 3. High-Affinity Cross-Sell Heatmap
Visualizing pairwise similarity scores between the base item and top recommendations.
"""))

    cells.append(code_cell("""
top_skus = [sample_sku] + [item['StockCode'] for item in similar_items]
sub_sim = recommender.similarity_df.loc[top_skus, top_skus]
labels = [recommender.product_catalog[s]['Description'][:22] for s in top_skus]

plt.figure(figsize=(8, 6))
sns.heatmap(sub_sim, annot=True, cmap='YlGnBu', xticklabels=labels, yticklabels=labels, fmt='.2f')
plt.title('Regency Collection Pairwise Cosine Affinity', fontsize=13, weight='bold')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()
"""))

    # Cell 6: User-Personalized Recommendation
    cells.append(md_cell("""
## 4. User-Personalized Recommendations
For an existing customer (e.g. `17850`), we aggregate their past basket vectors and recommend novel, unpurchased items with the highest cumulative affinity.
"""))

    cells.append(code_cell("""
customer_id = "17850"
past_purchases = recommender.customer_baskets.get(customer_id, set())
print(f"Customer {customer_id} has previously purchased {len(past_purchases)} distinct products.")

user_recs = recommender.recommend_for_customer(customer_id, top_n=5)
pd.DataFrame(user_recs)
"""))

    # Cell 7: Cold-Start Fallback
    cells.append(md_cell("""
## 5. Cold-Start Problem & Popularity Fallback
For anonymous visitors or new accounts with zero prior interactions, the system defaults to high-velocity catalog staples.
"""))

    cells.append(code_cell("""
cold_start_recs = recommender.get_cold_start_recommendations(top_n=5)
pd.DataFrame(cold_start_recs)
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
