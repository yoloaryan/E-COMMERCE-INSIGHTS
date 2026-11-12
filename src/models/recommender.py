"""
Product Recommendation Engine using Item-Based Collaborative Filtering.

Constructs sparse customer-product interaction matrices, computes high-dimensional
cosine similarity across SKUs, and generates both item-to-item cross-sell
recommendations and personalized user recommendations with cold-start fallbacks.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
import joblib

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
CUSTOMER_CENTRIC_PATH = PROCESSED_DATA_DIR / "online_retail_customer_centric.csv"


class ProductRecommender:
    """
    Industry-Standard Item-Based Collaborative Filtering:
    1. Interaction Matrix: Implicit feedback (Quantity bought per Customer x SKU).
    2. Cosine Similarity Matrix: Computes pairwise vector affinities across SKUs.
    3. Item-to-Item Recommender: 'Customers Who Bought This Also Bought...'.
    4. User-Personalized Recommender: Aggregates affinities across customer's historical basket.
    5. Cold-Start Fallback: Highest velocity popular catalog items.
    """

    def __init__(self, data_path: Path = CUSTOMER_CENTRIC_PATH, min_interactions: int = 5):
        self.data_path = data_path
        self.min_interactions = min_interactions
        self.df: pd.DataFrame = None
        self.product_catalog: dict = {}
        self.popularity_ranking: list = []
        self.item_user_matrix: csr_matrix = None
        self.similarity_df: pd.DataFrame = None
        self.customer_baskets: dict = {}
        self.unique_items: list = []

    def load_and_preprocess(self):
        """Loads clean customer transactions and filters low-support items."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Customer dataset not found at {self.data_path}.")
        self.df = pd.read_csv(
            self.data_path,
            dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str}
        )

        # Build clean Product Catalog mapping: StockCode -> Description & UnitPrice
        product_meta = (
            self.df.groupby("StockCode")
            .agg(
                Description=("Description", "first"),
                UnitPrice=("UnitPrice", "median"),
                TotalOrders=("InvoiceNo", "nunique"),
                TotalUnits=("Quantity", "sum")
            )
            .reset_index()
        )
        self.product_catalog = {
            row["StockCode"]: {
                "Description": row["Description"],
                "UnitPrice": round(row["UnitPrice"], 2),
                "TotalOrders": int(row["TotalOrders"])
            }
            for _, row in product_meta.iterrows()
        }

        # Build Popularity Ranking for Cold-Start Fallback
        self.popularity_ranking = (
            product_meta.sort_values(by="TotalOrders", ascending=False)["StockCode"]
            .tolist()
        )

        # Filter items with sufficient transactional support (at least min_interactions unique orders)
        valid_items_set = set(product_meta.loc[product_meta["TotalOrders"] >= self.min_interactions, "StockCode"])
        self.df_filtered = self.df[self.df["StockCode"].isin(valid_items_set)].copy()

        # Build customer historical basket map: CustomerID -> set(StockCodes)
        self.customer_baskets = (
            self.df_filtered.groupby("CustomerID")["StockCode"]
            .apply(set)
            .to_dict()
        )

        print(f"[Recommender] Loaded {len(self.df_filtered):,} transactions across {len(self.customer_baskets):,} customers.")
        print(f"[Recommender] Active candidate catalog: {len(valid_items_set):,} SKUs (min {self.min_interactions} purchases).")

    def build_similarity_matrix(self) -> pd.DataFrame:
        """
        Creates customer-item interaction matrix and computes pairwise cosine similarity.
        """
        if self.df is None:
            self.load_and_preprocess()

        # Pivot: Rows = StockCode, Columns = CustomerID, Values = Total Quantity (or 1 for binary implicit)
        # Using binary implicit feedback (bought vs not bought) provides cleaner affinity than raw volume spikes
        interactions = (
            self.df_filtered.groupby(["StockCode", "CustomerID"])["Quantity"]
            .sum()
            .reset_index()
        )
        interactions["Purchased"] = 1  # Binary implicit feedback

        pivot = interactions.pivot(index="StockCode", columns="CustomerID", values="Purchased").fillna(0)
        self.unique_items = pivot.index.tolist()

        # Sparse matrix computation
        sparse_pivot = csr_matrix(pivot.values)
        print(f"[Recommender] Computing pairwise Cosine Similarity matrix for {len(self.unique_items)} SKUs...")
        cosine_sim = cosine_similarity(sparse_pivot)

        self.similarity_df = pd.DataFrame(
            cosine_sim,
            index=self.unique_items,
            columns=self.unique_items
        )

        # Serialize matrices and catalog
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        sim_path = MODELS_DIR / "item_similarity_matrix.joblib"
        catalog_path = MODELS_DIR / "product_catalog.joblib"
        joblib.dump(self.similarity_df, sim_path, compress=3)
        joblib.dump(self.product_catalog, catalog_path)
        print(f"[Recommender] Serialized Item Similarity Matrix to: {sim_path}")
        print(f"[Recommender] Serialized Product Catalog to: {catalog_path}")

        return self.similarity_df

    def recommend_similar_items(self, stock_code: str, top_n: int = 5) -> list:
        """
        Item-to-Item Cross-Sell ('Customers Who Bought This Also Bought...').
        """
        stock_code = str(stock_code).strip().upper()
        if self.similarity_df is None:
            self.build_similarity_matrix()

        if stock_code not in self.similarity_df.index:
            # Cold-start fallback
            return self.get_cold_start_recommendations(top_n)

        # Get similarities, exclude the item itself
        sim_scores = self.similarity_df.loc[stock_code].drop(stock_code).sort_values(ascending=False).head(top_n)

        recommendations = []
        for sku, score in sim_scores.items():
            meta = self.product_catalog.get(sku, {"Description": "Unknown SKU", "UnitPrice": 0.0})
            recommendations.append({
                "StockCode": sku,
                "Description": meta["Description"],
                "UnitPrice": meta["UnitPrice"],
                "SimilarityScore": round(float(score), 4)
            })

        return recommendations

    def recommend_for_customer(self, customer_id: str, top_n: int = 5) -> list:
        """
        Personalized User Recommendations:
        Aggregates affinity scores for all items the customer has previously purchased,
        then filters out items already in their purchase history.
        """
        customer_id = str(customer_id).strip()
        if self.similarity_df is None:
            self.build_similarity_matrix()

        purchased_items = self.customer_baskets.get(customer_id, set())

        if not purchased_items:
            # Customer has no prior history -> Cold-Start fallback
            return self.get_cold_start_recommendations(top_n)

        # Filter to items that exist in our similarity matrix
        valid_purchased = [sku for sku in purchased_items if sku in self.similarity_df.index]
        if not valid_purchased:
            return self.get_cold_start_recommendations(top_n)

        # Sum affinity vectors for all purchased items
        customer_affinity_scores = self.similarity_df.loc[valid_purchased].sum(axis=0)

        # Exclude items the customer has already purchased
        unseen_scores = customer_affinity_scores.drop(labels=valid_purchased, errors="ignore")
        top_skus = unseen_scores.sort_values(ascending=False).head(top_n)

        recommendations = []
        for sku, score in top_skus.items():
            meta = self.product_catalog.get(sku, {"Description": "Unknown SKU", "UnitPrice": 0.0})
            recommendations.append({
                "StockCode": sku,
                "Description": meta["Description"],
                "UnitPrice": meta["UnitPrice"],
                "AggregatedAffinityScore": round(float(score), 4)
            })

        return recommendations

    def get_cold_start_recommendations(self, top_n: int = 5) -> list:
        """Fallback for unknown products or new visitors using high-velocity staples."""
        recommendations = []
        for sku in self.popularity_ranking[:top_n]:
            meta = self.product_catalog.get(sku, {"Description": "Unknown SKU", "UnitPrice": 0.0})
            recommendations.append({
                "StockCode": sku,
                "Description": meta["Description"],
                "UnitPrice": meta["UnitPrice"],
                "Strategy": "Cold-Start (Top Platform Bestseller)"
            })
        return recommendations


if __name__ == "__main__":
    recommender = ProductRecommender(min_interactions=5)
    recommender.load_and_preprocess()
    recommender.build_similarity_matrix()

    # 1. Test Item-to-Item Cross Sell: Regency Cakestand 3 Tier (StockCode: 22423)
    sample_sku = "22423"
    sku_desc = recommender.product_catalog[sample_sku]["Description"]
    print(f"\n--- ITEM-TO-ITEM RECOMMENDATIONS FOR: [{sample_sku}] {sku_desc} ---")
    similar_items = recommender.recommend_similar_items(sample_sku, top_n=5)
    for i, item in enumerate(similar_items, 1):
        print(f"  {i}. [{item['StockCode']}] {item['Description']} (₹{item['UnitPrice']}) | Sim: {item['SimilarityScore']}")

    # 2. Test Personalized Customer Recommendation (e.g. Customer 17850)
    sample_cid = "17850"
    print(f"\n--- PERSONALIZED RECOMMENDATIONS FOR CUSTOMER ID: {sample_cid} ---")
    user_recs = recommender.recommend_for_customer(sample_cid, top_n=5)
    for i, item in enumerate(user_recs, 1):
        print(f"  {i}. [{item['StockCode']}] {item['Description']} (₹{item['UnitPrice']}) | Score: {item['AggregatedAffinityScore']}")
