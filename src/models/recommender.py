"""
Industry-Standard Hybrid Recommender System (Phase 31).

Combines:
1. Latent Factor Matrix Factorization (TruncatedSVD, k=20) on implicit user-item interactions.
2. High-dimensional Item-Item Collaborative Filtering (Cosine Similarity).
3. Profit Margin Optimization (Category-calibrated gross margin rates).
4. Category Affinity & Contextual Basket Scoring.
5. Cold-Start Multi-Category Popularity Diversification.
"""

from pathlib import Path
import sys
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("nexus.recommender")

PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"
CUSTOMER_CENTRIC_PATH = PROCESSED_DATA_DIR / "online_retail_customer_centric.csv"
PARQUET_PATH = PROCESSED_DATA_DIR / "online_retail_cleaned.parquet"

# Standard GBP to INR conversion rate used throughout the platform
GBP_TO_INR = 105.0

# Calibrated Gross Margin Rates by Category
CATEGORY_MARGIN_RATES: Dict[str, float] = {
    "Kitchen & Dining": 0.45,
    "Home Decor & Lighting": 0.50,
    "Party & Seasonal": 0.55,
    "Bags & Storage": 0.48,
    "Gifts & General Merchandise": 0.42,
}

# Multi-Objective Weights: (svd, cf, margin, category)
OBJECTIVE_WEIGHTS: Dict[str, Tuple[float, float, float, float]] = {
    "balanced": (0.40, 0.30, 0.15, 0.15),
    "margin_max": (0.20, 0.15, 0.55, 0.10),
    "discovery": (0.50, 0.15, 0.10, 0.25),
}


import re

def categorize_product_desc(desc: str) -> Tuple[str, float]:
    """Assigns retail merchandise category and gross margin rate from product description."""
    d = str(desc or "").upper()
    tokens = set(re.findall(r"\b[A-Z0-9-]+\b", d))

    if any(k in d for k in ("BUNTING", "CHRISTMAS", "PAPER CHAIN", "PARTY", "BIRTHDAY", "GARLAND", "WRAP", "CRACKER", "SNOWFLAKE", "EASTER", "BALLOON", "CONFETTI")) or "TAG" in tokens or "CARD" in tokens:
        cat = "Party & Seasonal"
    elif any(k in d for k in ("CAKESTAND", "TEACUP", "PANTRY", "LUNCH BAG", "PLATE", "BOWL", "CUTLERY", "DISH", "SAUCER", "COFFEE", "BAKING")) or any(k in tokens for k in ("TIN", "TINS", "MUG", "MUGS", "JAR", "JARS", "JUG", "JUGS", "TEA")):
        cat = "Kitchen & Dining"
    elif any(k in d for k in ("T-LIGHT", "LANTERN", "HEART", "CANDLE", "ORNAMENT", "MIRROR", "FRAME", "CLOCK", "CUSHION", "VASE", "WALL", "HANGER", "SIGN", "DOORMAT", "LIGHT")):
        cat = "Home Decor & Lighting"
    elif any(k in d for k in ("JUMBO BAG", "STORAGE", "SHOPPER", "BACKPACK", "TOTE", "BASKET", "TRUNK")) or any(k in tokens for k in ("BOX", "BOXES", "CASE", "CASES")):
        cat = "Bags & Storage"
    else:
        cat = "Gifts & General Merchandise"

    margin_rate = CATEGORY_MARGIN_RATES.get(cat, 0.42)
    return cat, margin_rate


class ProductRecommender:
    """
    Production Hybrid Next-Best-SKU Recommender:
    - TruncatedSVD Latent Factor Matrix Factorization (k=20).
    - Item-Item Sparse Cosine Similarity Matrix.
    - Multi-Objective Ranking (Balanced, Margin-Max, Discovery).
    - Real-Time Basket Cross-Sell & Cold-Start Catalog Fallbacks.
    - Exact Score Breakdown Explanations.
    """

    def __init__(
        self,
        data_path: Optional[Path] = None,
        min_interactions: int = 3,
        n_svd_components: int = 20,
    ):
        if data_path is None:
            data_path = CUSTOMER_CENTRIC_PATH if CUSTOMER_CENTRIC_PATH.exists() else PARQUET_PATH
        self.data_path = Path(data_path)
        self.min_interactions = min_interactions
        self.n_svd_components = n_svd_components

        # Data structures
        self.df: Optional[pd.DataFrame] = None
        self.product_catalog: Dict[str, Dict[str, Any]] = {}
        self.popularity_ranking: List[str] = []
        self.similarity_df: Optional[pd.DataFrame] = None
        self.customer_baskets: Dict[str, Set[str]] = {}
        self.customer_categories: Dict[str, Dict[str, int]] = {}
        self.customer_spend: Dict[str, float] = {}
        self.customer_countries: Dict[str, str] = {}
        self.unique_items: List[str] = []
        self.unique_customers: List[str] = []

        # SVD model components
        self.svd_model: Optional[TruncatedSVD] = None
        self.user_factors: Optional[np.ndarray] = None  # (n_users, k)
        self.item_factors: Optional[np.ndarray] = None  # (k, n_items)
        self.customer_to_idx: Dict[str, int] = {}
        self.item_to_idx: Dict[str, int] = {}
        self.explained_variance_ratio: float = 0.0
        self.svd_trained_at: Optional[str] = None

    def load_and_preprocess(self):
        """Loads clean customer transactions, enriches catalog with margins & categories."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found at {self.data_path}")

        if str(self.data_path).endswith(".parquet"):
            raw_df = pd.read_parquet(self.data_path)
        else:
            raw_df = pd.read_csv(
                self.data_path,
                dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str},
            )

        # Clean customer IDs
        raw_df = raw_df.dropna(subset=["CustomerID"]).copy()
        raw_df["CustomerID"] = (
            raw_df["CustomerID"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )
        raw_df = raw_df[~raw_df["CustomerID"].isin(["", "None", "nan", "GUEST"])].copy()
        raw_df["StockCode"] = raw_df["StockCode"].astype(str).str.strip().str.upper()
        raw_df["Quantity"] = pd.to_numeric(raw_df["Quantity"], errors="coerce").fillna(0)
        raw_df["UnitPrice"] = pd.to_numeric(raw_df["UnitPrice"], errors="coerce").fillna(0.0)
        raw_df["TotalPrice"] = pd.to_numeric(raw_df.get("TotalPrice", raw_df["Quantity"] * raw_df["UnitPrice"]), errors="coerce").fillna(0.0)

        # Filter cancelled or non-positive
        self.df = raw_df[(raw_df["Quantity"] > 0) & (raw_df["UnitPrice"] > 0)].copy()

        # Build clean Product Catalog mapping: StockCode -> Metadata
        product_meta = (
            self.df.groupby("StockCode")
            .agg(
                Description=("Description", "first"),
                UnitPrice=("UnitPrice", "median"),
                TotalOrders=("InvoiceNo", "nunique"),
                TotalUnits=("Quantity", "sum"),
                TotalRevenue=("TotalPrice", "sum"),
            )
            .reset_index()
        )

        catalog: Dict[str, Dict[str, Any]] = {}
        for _, row in product_meta.iterrows():
            sku = str(row["StockCode"])
            desc = str(row["Description"])
            price_gbp = round(float(row["UnitPrice"]), 2)
            cat, margin_rate = categorize_product_desc(desc)
            unit_margin_gbp = round(price_gbp * margin_rate, 2)

            catalog[sku] = {
                "StockCode": sku,
                "Description": desc,
                "UnitPrice": price_gbp,
                "UnitPriceGBP": price_gbp,
                "UnitPriceINR": round(price_gbp * GBP_TO_INR, 2),
                "Category": cat,
                "GrossMarginRate": margin_rate,
                "EstimatedUnitMarginGBP": unit_margin_gbp,
                "EstimatedUnitMarginINR": round(unit_margin_gbp * GBP_TO_INR, 2),
                "TotalOrders": int(row["TotalOrders"]),
                "TotalUnits": int(row["TotalUnits"]),
                "TotalRevenueGBP": round(float(row["TotalRevenue"]), 2),
            }
        self.product_catalog = catalog

        # Build Popularity Ranking
        self.popularity_ranking = (
            product_meta.sort_values(by="TotalOrders", ascending=False)["StockCode"]
            .tolist()
        )

        # Filter items with sufficient transactional support
        valid_items_set = set(
            product_meta.loc[product_meta["TotalOrders"] >= self.min_interactions, "StockCode"]
        )
        self.df_filtered = self.df[self.df["StockCode"].isin(valid_items_set)].copy()

        # Build Customer History Profiles
        self.customer_baskets = (
            self.df_filtered.groupby("CustomerID")["StockCode"]
            .apply(set)
            .to_dict()
        )
        self.customer_spend = (
            self.df_filtered.groupby("CustomerID")["TotalPrice"]
            .sum()
            .round(2)
            .to_dict()
        )
        self.customer_countries = (
            self.df_filtered.groupby("CustomerID")["Country"]
            .first()
            .to_dict()
        )

        # Build Customer Category Preference Map
        cust_cats: Dict[str, Dict[str, int]] = {}
        for _, r in self.df_filtered.iterrows():
            cid = r["CustomerID"]
            sku = r["StockCode"]
            c_meta = self.product_catalog.get(sku)
            if not c_meta:
                continue
            cat = c_meta["Category"]
            if cid not in cust_cats:
                cust_cats[cid] = {}
            cust_cats[cid][cat] = cust_cats[cid].get(cat, 0) + 1
        self.customer_categories = cust_cats

        self.unique_customers = sorted(list(self.customer_baskets.keys()))
        self.unique_items = sorted(list(valid_items_set))
        self.customer_to_idx = {c: i for i, c in enumerate(self.unique_customers)}
        self.item_to_idx = {it: j for j, it in enumerate(self.unique_items)}

        logger.info(
            f"[Recommender] Loaded {len(self.df_filtered):,} transactions across "
            f"{len(self.unique_customers):,} customer accounts and {len(self.unique_items):,} SKUs."
        )

    def build_similarity_matrix(self) -> pd.DataFrame:
        """Constructs Item-Item Cosine Similarity matrix on binary implicit interactions."""
        if self.df is None or not self.unique_items:
            self.load_and_preprocess()

        interactions = (
            self.df_filtered.groupby(["StockCode", "CustomerID"])["Quantity"]
            .sum()
            .reset_index()
        )
        interactions["Purchased"] = 1

        pivot = (
            interactions.pivot(index="StockCode", columns="CustomerID", values="Purchased")
            .reindex(index=self.unique_items, columns=self.unique_customers)
            .fillna(0)
        )

        sparse_pivot = csr_matrix(pivot.values)
        logger.info(f"[Recommender] Computing Cosine Similarity for {len(self.unique_items)} SKUs...")
        cosine_sim = cosine_similarity(sparse_pivot)

        self.similarity_df = pd.DataFrame(
            cosine_sim,
            index=self.unique_items,
            columns=self.unique_items,
        )

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.similarity_df, MODELS_DIR / "item_similarity_matrix.joblib", compress=3)
        joblib.dump(self.product_catalog, MODELS_DIR / "product_catalog.joblib")
        return self.similarity_df

    def fit_svd(self, n_components: Optional[int] = None) -> Dict[str, Any]:
        """
        Fits TruncatedSVD Latent Factor Matrix Factorization on log-transformed interaction matrix.
        X = U * Sigma * V^T, shape (N_users, N_items).
        """
        if self.df is None or not self.unique_items:
            self.load_and_preprocess()

        k = n_components or self.n_svd_components
        k = min(k, len(self.unique_items) - 1, len(self.unique_customers) - 1)

        # Log1p quantity matrix
        agg = (
            self.df_filtered.groupby(["CustomerID", "StockCode"])["Quantity"]
            .sum()
            .reset_index()
        )
        agg["Rating"] = np.log1p(np.maximum(1, agg["Quantity"].values))

        rows = agg["CustomerID"].map(self.customer_to_idx).values
        cols = agg["StockCode"].map(self.item_to_idx).values
        vals = agg["Rating"].values

        X = csr_matrix(
            (vals, (rows, cols)),
            shape=(len(self.unique_customers), len(self.unique_items)),
        )

        t0 = time.perf_counter()
        self.svd_model = TruncatedSVD(n_components=k, random_state=42)
        self.user_factors = self.svd_model.fit_transform(X)  # shape (n_users, k)
        self.item_factors = self.svd_model.components_       # shape (k, n_items)
        self.explained_variance_ratio = float(self.svd_model.explained_variance_ratio_.sum())
        elapsed = round((time.perf_counter() - t0) * 1000.0, 2)
        self.svd_trained_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Save SVD bundle to disk
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        bundle = {
            "svd_model": self.svd_model,
            "user_factors": self.user_factors,
            "item_factors": self.item_factors,
            "explained_variance_ratio": self.explained_variance_ratio,
            "unique_customers": self.unique_customers,
            "unique_items": self.unique_items,
            "customer_to_idx": self.customer_to_idx,
            "item_to_idx": self.item_to_idx,
            "customer_baskets": self.customer_baskets,
            "customer_categories": self.customer_categories,
            "customer_spend": self.customer_spend,
            "customer_countries": self.customer_countries,
            "product_catalog": self.product_catalog,
            "popularity_ranking": self.popularity_ranking,
            "svd_trained_at": self.svd_trained_at,
        }
        joblib.dump(bundle, MODELS_DIR / "svd_recommender.joblib", compress=3)
        logger.info(
            f"[Recommender] Fitted TruncatedSVD(k={k}) in {elapsed}ms. "
            f"Explained Variance: {self.explained_variance_ratio * 100:.2f}%."
        )

        return {
            "n_components": k,
            "explained_variance_ratio": self.explained_variance_ratio,
            "explained_variance_pct": round(self.explained_variance_ratio * 100.0, 2),
            "training_duration_ms": elapsed,
            "customers_indexed": len(self.unique_customers),
            "items_indexed": len(self.unique_items),
        }

    def load_artifacts_if_present(self) -> bool:
        """Loads precomputed SVD bundle and similarity matrix if available on disk."""
        svd_path = MODELS_DIR / "svd_recommender.joblib"
        sim_path = MODELS_DIR / "item_similarity_matrix.joblib"
        cat_path = MODELS_DIR / "product_catalog.joblib"

        loaded_svd = False
        if svd_path.exists():
            try:
                bundle = joblib.load(svd_path)
                self.svd_model = bundle.get("svd_model")
                self.user_factors = bundle.get("user_factors")
                self.item_factors = bundle.get("item_factors")
                self.explained_variance_ratio = bundle.get("explained_variance_ratio", 0.24)
                self.unique_customers = bundle.get("unique_customers", [])
                self.unique_items = bundle.get("unique_items", [])
                self.customer_to_idx = bundle.get("customer_to_idx", {})
                self.item_to_idx = bundle.get("item_to_idx", {})
                self.customer_baskets = bundle.get("customer_baskets", {})
                self.customer_categories = bundle.get("customer_categories", {})
                self.customer_spend = bundle.get("customer_spend", {})
                self.customer_countries = bundle.get("customer_countries", {})
                self.product_catalog = bundle.get("product_catalog", {})
                self.popularity_ranking = bundle.get("popularity_ranking", [])
                self.svd_trained_at = bundle.get("svd_trained_at")
                loaded_svd = True
            except Exception as exc:
                logger.warning(f"[Recommender] Failed to load svd_recommender.joblib: {exc}")

        if sim_path.exists() and self.similarity_df is None:
            try:
                self.similarity_df = joblib.load(sim_path)
                if not self.unique_items:
                    self.unique_items = list(self.similarity_df.index)
            except Exception as exc:
                logger.warning(f"[Recommender] Failed to load item_similarity_matrix.joblib: {exc}")

        if cat_path.exists() and not self.product_catalog:
            try:
                raw_cat = joblib.load(cat_path)
                # Enrich if missing Category or INR
                enriched = {}
                for sku, info in raw_cat.items():
                    price = float(info.get("UnitPrice", 0.0))
                    desc = info.get("Description", "Catalog Item")
                    cat, rate = categorize_product_desc(desc)
                    unit_m_gbp = round(price * rate, 2)
                    enriched[sku] = {
                        "StockCode": sku,
                        "Description": desc,
                        "UnitPrice": price,
                        "UnitPriceGBP": price,
                        "UnitPriceINR": round(price * GBP_TO_INR, 2),
                        "Category": info.get("Category", cat),
                        "GrossMarginRate": info.get("GrossMarginRate", rate),
                        "EstimatedUnitMarginGBP": info.get("EstimatedUnitMarginGBP", unit_m_gbp),
                        "EstimatedUnitMarginINR": info.get("EstimatedUnitMarginINR", round(unit_m_gbp * GBP_TO_INR, 2)),
                        "TotalOrders": info.get("TotalOrders", 1),
                    }
                self.product_catalog = enriched
                if not self.popularity_ranking:
                    self.popularity_ranking = list(self.product_catalog.keys())[:50]
            except Exception as exc:
                logger.warning(f"[Recommender] Failed to load product_catalog.joblib: {exc}")

        return loaded_svd and self.similarity_df is not None

    def ensure_ready(self):
        """Ensures both SVD model and similarity matrix are initialized."""
        if self.svd_model is not None and self.similarity_df is not None and self.product_catalog:
            return

        if self.load_artifacts_if_present():
            return

        logger.info("[Recommender] Artifacts not complete on disk. Training from clean dataset...")
        self.load_and_preprocess()
        self.build_similarity_matrix()
        self.fit_svd()

    # -------------------------------------------------------------------------
    # Core Recommendation Algorithms
    # -------------------------------------------------------------------------

    def recommend_similar_items(self, stock_code: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Item-to-Item Cross-Sell ('Customers Who Bought This Also Bought...')."""
        self.ensure_ready()
        stock_code = str(stock_code).strip().upper()

        if self.similarity_df is None or stock_code not in self.similarity_df.index:
            return self.get_cold_start_recommendations(top_n)

        sim_scores = (
            self.similarity_df.loc[stock_code]
            .drop(stock_code, errors="ignore")
            .sort_values(ascending=False)
            .head(top_n)
        )

        recs = []
        for sku, score in sim_scores.items():
            meta = self._get_item_metadata(sku)
            margin_rate = meta.get("GrossMarginRate", 0.42)
            unit_price_gbp = meta.get("UnitPriceGBP", meta.get("UnitPrice", 0.0))
            margin_gbp = round(unit_price_gbp * margin_rate, 2)
            recs.append({
                "StockCode": sku,
                "Description": meta.get("Description", "Catalog Item"),
                "Category": meta.get("Category", "Gifts & General Merchandise"),
                "UnitPrice": unit_price_gbp,
                "UnitPriceGBP": unit_price_gbp,
                "UnitPriceINR": round(unit_price_gbp * GBP_TO_INR, 2),
                "GrossMarginRate": margin_rate,
                "EstimatedUnitMarginGBP": margin_gbp,
                "EstimatedUnitMarginINR": round(margin_gbp * GBP_TO_INR, 2),
                "SimilarityScore": round(float(score), 4),
                "Explanation": f"Strong cross-sell co-purchase frequency ({round(float(score)*100, 1)}% affinity).",
            })
        return recs

    def recommend_for_customer(self, customer_id: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Personalized User Recommendations (Backward compatible signature, calls hybrid engine)."""
        return self.recommend_next_best_skus(
            customer_id=customer_id,
            top_n=top_n,
            objective="balanced",
        )

    def recommend_next_best_skus(
        self,
        customer_id: Optional[str] = None,
        current_basket: Optional[List[str]] = None,
        top_n: int = 5,
        objective: str = "balanced",
    ) -> List[Dict[str, Any]]:
        """
        Industry-Standard Next-Best-SKU Hybrid Engine:
        Combines SVD Latent Affinity + Collaborative Filtering + Profit Margin + Category Affinity.
        Objectives:
          - 'balanced': Equal harmony between customer relevance and business margin.
          - 'margin_max': Aggressively prioritizes high-margin profit-accretive up-sells.
          - 'discovery': Focuses on latent factor novelty and broad category exploration.
        """
        self.ensure_ready()
        cid = str(customer_id).strip() if customer_id else None
        basket = [str(s).strip().upper() for s in (current_basket or []) if s]
        obj = objective.lower() if objective in OBJECTIVE_WEIGHTS else "balanced"
        w_svd, w_cf, w_margin, w_cat = OBJECTIVE_WEIGHTS[obj]

        purchased_items: Set[str] = set()
        user_cat_dist: Dict[str, float] = {}

        # 1. Determine customer latent vector
        user_latent_vec: Optional[np.ndarray] = None
        if cid and cid in self.customer_to_idx and self.user_factors is not None:
            u_idx = self.customer_to_idx[cid]
            user_latent_vec = self.user_factors[u_idx]
            purchased_items.update(self.customer_baskets.get(cid, set()))

            cat_counts = self.customer_categories.get(cid, {})
            total_orders = max(1, sum(cat_counts.values()))
            user_cat_dist = {cat: count / total_orders for cat, count in cat_counts.items()}
        elif basket and self.svd_model is not None and self.item_factors is not None:
            # On-the-fly SVD transform of live shopping basket
            basket_vec = np.zeros((1, len(self.unique_items)))
            for sku in basket:
                if sku in self.item_to_idx:
                    basket_vec[0, self.item_to_idx[sku]] = 1.0
            if basket_vec.sum() > 0:
                user_latent_vec = self.svd_model.transform(csr_matrix(basket_vec))[0]
            purchased_items.update(basket)

        # 2. Check for cold-start (unknown customer and empty basket)
        if user_latent_vec is None and not basket:
            return self.get_cold_start_recommendations(top_n, objective=obj)

        # 3. Compute SVD Latent Scores across candidate items
        candidate_skus = [it for it in self.unique_items if it not in purchased_items]
        if not candidate_skus:
            candidate_skus = self.unique_items

        cand_indices = [self.item_to_idx[it] for it in candidate_skus if it in self.item_to_idx]
        if user_latent_vec is not None and self.item_factors is not None:
            raw_svd_all = user_latent_vec @ self.item_factors  # (n_items,)
            raw_svd = raw_svd_all[cand_indices]
            # Normalize to [0, 1]
            min_svd, max_svd = np.min(raw_svd), np.max(raw_svd)
            if max_svd > min_svd:
                norm_svd = (raw_svd - min_svd) / (max_svd - min_svd)
            else:
                norm_svd = np.ones_like(raw_svd) * 0.5
        else:
            norm_svd = np.zeros(len(cand_indices))

        # 4. Compute Collaborative Filtering (Cosine Similarity) Scores
        anchor_skus = list(purchased_items if purchased_items else basket)
        valid_anchors = [
            sku for sku in anchor_skus
            if self.similarity_df is not None and sku in self.similarity_df.index
        ]

        if valid_anchors and self.similarity_df is not None:
            cf_sums = self.similarity_df.loc[valid_anchors, candidate_skus].sum(axis=0).values
            min_cf, max_cf = np.min(cf_sums), np.max(cf_sums)
            if max_cf > min_cf:
                norm_cf = (cf_sums - min_cf) / (max_cf - min_cf)
            else:
                norm_cf = np.ones_like(cf_sums) * 0.5
        else:
            norm_cf = np.zeros(len(cand_indices))

        # 5. Compute Profit Margin Scores & Category Match
        norm_margins = []
        norm_cats = []
        for sku in candidate_skus:
            meta = self._get_item_metadata(sku)
            margin_gbp = meta.get("EstimatedUnitMarginGBP", 1.0)
            cat = meta.get("Category", "Gifts & General Merchandise")
            norm_margins.append(min(1.0, margin_gbp / 15.0))  # Capped at £15 unit margin
            norm_cats.append(user_cat_dist.get(cat, 0.20))

        norm_margins = np.array(norm_margins)
        norm_cats = np.array(norm_cats)

        # 6. Composite Hybrid Score
        hybrid_scores = (
            w_svd * norm_svd
            + w_cf * norm_cf
            + w_margin * norm_margins
            + w_cat * norm_cats
        )

        # 7. Select Top-N
        ranked_local_indices = np.argsort(hybrid_scores)[-top_n:][::-1]
        recs: List[Dict[str, Any]] = []

        for rank, l_idx in enumerate(ranked_local_indices, start=1):
            sku = candidate_skus[l_idx]
            meta = self._get_item_metadata(sku)
            h_score = float(hybrid_scores[l_idx])
            s_svd = float(norm_svd[l_idx])
            s_cf = float(norm_cf[l_idx])
            s_margin = float(norm_margins[l_idx])
            s_cat = float(norm_cats[l_idx])

            # Determine Explanation Badge
            badge, reason = self._explain_badge(
                s_svd, s_cf, s_margin, s_cat, meta.get("Category", ""), obj
            )

            unit_price_gbp = meta.get("UnitPriceGBP", meta.get("UnitPrice", 0.0))
            margin_rate = meta.get("GrossMarginRate", 0.42)
            margin_gbp = meta.get("EstimatedUnitMarginGBP", round(unit_price_gbp * margin_rate, 2))

            recs.append({
                "Rank": rank,
                "StockCode": sku,
                "Description": meta.get("Description", "Catalog Item"),
                "Category": meta.get("Category", "Gifts & General Merchandise"),
                "UnitPrice": unit_price_gbp,
                "UnitPriceGBP": unit_price_gbp,
                "UnitPriceINR": round(unit_price_gbp * GBP_TO_INR, 2),
                "GrossMarginRate": margin_rate,
                "EstimatedUnitMarginGBP": margin_gbp,
                "EstimatedUnitMarginINR": round(margin_gbp * GBP_TO_INR, 2),
                "HybridScore": round(h_score, 4),
                "ScoreBreakdown": {
                    "svd_latent_affinity": round(s_svd, 3),
                    "collaborative_cross_sell": round(s_cf, 3),
                    "margin_contribution": round(s_margin, 3),
                    "category_affinity": round(s_cat, 3),
                },
                "ExplanationBadge": badge,
                "Explanation": reason,
            })

        return recs

    def recommend_for_basket(
        self,
        current_cart_skus: List[str],
        customer_id: Optional[str] = None,
        top_n: int = 5,
        objective: str = "balanced",
    ) -> Dict[str, Any]:
        """Scores an active shopping cart and returns optimal complementary add-ons with margin impact."""
        self.ensure_ready()
        cart_skus = [str(s).strip().upper() for s in current_cart_skus if s]

        # Calculate current basket financials
        cart_items_meta = [self._get_item_metadata(s) for s in cart_skus]
        cart_subtotal_gbp = sum(m.get("UnitPriceGBP", m.get("UnitPrice", 0.0)) for m in cart_items_meta)
        cart_margin_gbp = sum(m.get("EstimatedUnitMarginGBP", 0.0) for m in cart_items_meta)

        recs = self.recommend_next_best_skus(
            customer_id=customer_id,
            current_basket=cart_skus,
            top_n=top_n,
            objective=objective,
        )

        projected_lift_gbp = sum(r["EstimatedUnitMarginGBP"] for r in recs[:2])
        return {
            "cart_skus": cart_skus,
            "cart_item_count": len(cart_skus),
            "cart_subtotal_gbp": round(cart_subtotal_gbp, 2),
            "cart_subtotal_inr": round(cart_subtotal_gbp * GBP_TO_INR, 2),
            "cart_estimated_margin_gbp": round(cart_margin_gbp, 2),
            "cart_estimated_margin_inr": round(cart_margin_gbp * GBP_TO_INR, 2),
            "objective_used": objective,
            "projected_top2_margin_lift_gbp": round(projected_lift_gbp, 2),
            "projected_top2_margin_lift_inr": round(projected_lift_gbp * GBP_TO_INR, 2),
            "recommendations": recs,
        }

    def explain_recommendation(
        self,
        customer_id: str,
        stock_code: str,
        objective: str = "balanced",
    ) -> Dict[str, Any]:
        """Provides full mathematical breakdown of why SKU is ranked for this customer."""
        self.ensure_ready()
        cid = str(customer_id).strip()
        sku = str(stock_code).strip().upper()
        meta = self._get_item_metadata(sku)

        # Run scoring for this single item
        recs = self.recommend_next_best_skus(
            customer_id=cid,
            top_n=25,
            objective=objective,
        )
        matched = next((r for r in recs if r["StockCode"] == sku), None)

        if matched:
            return {
                "customer_id": cid,
                "stock_code": sku,
                "objective": objective,
                "is_top_recommendation": True,
                "rank": matched["Rank"],
                "hybrid_score": matched["HybridScore"],
                "score_breakdown": matched["ScoreBreakdown"],
                "badge": matched["ExplanationBadge"],
                "explanation": matched["Explanation"],
                "item_meta": matched,
            }

        # If not in top 25, compute ad-hoc components
        w_svd, w_cf, w_margin, w_cat = OBJECTIVE_WEIGHTS.get(objective, OBJECTIVE_WEIGHTS["balanced"])
        s_svd = 0.5
        if cid in self.customer_to_idx and sku in self.item_to_idx and self.user_factors is not None:
            u_idx = self.customer_to_idx[cid]
            i_idx = self.item_to_idx[sku]
            raw = float(self.user_factors[u_idx] @ self.item_factors[:, i_idx])
            s_svd = max(0.0, min(1.0, (raw + 1.0) / 3.0))

        s_cf = 0.0
        b_items = self.customer_baskets.get(cid, set())
        if b_items and self.similarity_df is not None and sku in self.similarity_df.index:
            s_cf = float(self.similarity_df.loc[list(b_items), sku].mean())

        margin_gbp = meta.get("EstimatedUnitMarginGBP", 1.0)
        s_margin = min(1.0, margin_gbp / 15.0)

        cat = meta.get("Category", "Gifts & General Merchandise")
        cat_counts = self.customer_categories.get(cid, {})
        s_cat = cat_counts.get(cat, 0) / max(1, sum(cat_counts.values()))

        h_score = round(w_svd * s_svd + w_cf * s_cf + w_margin * s_margin + w_cat * s_cat, 4)
        badge, reason = self._explain_badge(s_svd, s_cf, s_margin, s_cat, cat, objective)

        return {
            "customer_id": cid,
            "stock_code": sku,
            "objective": objective,
            "is_top_recommendation": False,
            "rank": "> 25",
            "hybrid_score": h_score,
            "score_breakdown": {
                "svd_latent_affinity": round(s_svd, 3),
                "collaborative_cross_sell": round(s_cf, 3),
                "margin_contribution": round(s_margin, 3),
                "category_affinity": round(s_cat, 3),
            },
            "badge": badge,
            "explanation": reason,
            "item_meta": meta,
        }

    def get_cold_start_recommendations(
        self,
        top_n: int = 5,
        objective: str = "balanced",
    ) -> List[Dict[str, Any]]:
        """Multi-category diversified fallback for unknown accounts / new visitors."""
        recs = []
        seen_cats: Set[str] = set()

        # Prioritize 1 staple from each category first for broad merchandising balance
        for sku in self.popularity_ranking:
            meta = self._get_item_metadata(sku)
            cat = meta.get("Category", "Gifts & General Merchandise")
            if cat not in seen_cats:
                seen_cats.add(cat)
                unit_price = meta.get("UnitPriceGBP", meta.get("UnitPrice", 0.0))
                margin_rate = meta.get("GrossMarginRate", 0.42)
                margin_gbp = round(unit_price * margin_rate, 2)
                recs.append({
                    "Rank": len(recs) + 1,
                    "StockCode": sku,
                    "Description": meta.get("Description", "Catalog Item"),
                    "Category": cat,
                    "UnitPrice": unit_price,
                    "UnitPriceGBP": unit_price,
                    "UnitPriceINR": round(unit_price * GBP_TO_INR, 2),
                    "GrossMarginRate": margin_rate,
                    "EstimatedUnitMarginGBP": margin_gbp,
                    "EstimatedUnitMarginINR": round(margin_gbp * GBP_TO_INR, 2),
                    "HybridScore": 0.50,
                    "ScoreBreakdown": {
                        "svd_latent_affinity": 0.50,
                        "collaborative_cross_sell": 0.50,
                        "margin_contribution": round(min(1.0, margin_gbp / 15.0), 3),
                        "category_affinity": 0.50,
                    },
                    "ExplanationBadge": "Catalog Anchor",
                    "Explanation": f"High-velocity staple across {cat} ({meta.get('TotalOrders', 0)} platform orders).",
                })
            if len(recs) >= top_n:
                break

        # If more slots needed, take remaining top velocity items
        if len(recs) < top_n:
            for sku in self.popularity_ranking:
                if any(r["StockCode"] == sku for r in recs):
                    continue
                meta = self._get_item_metadata(sku)
                unit_price = meta.get("UnitPriceGBP", meta.get("UnitPrice", 0.0))
                margin_rate = meta.get("GrossMarginRate", 0.42)
                margin_gbp = round(unit_price * margin_rate, 2)
                recs.append({
                    "Rank": len(recs) + 1,
                    "StockCode": sku,
                    "Description": meta.get("Description", "Catalog Item"),
                    "Category": meta.get("Category", "Gifts & General Merchandise"),
                    "UnitPrice": unit_price,
                    "UnitPriceGBP": unit_price,
                    "UnitPriceINR": round(unit_price * GBP_TO_INR, 2),
                    "GrossMarginRate": margin_rate,
                    "EstimatedUnitMarginGBP": margin_gbp,
                    "EstimatedUnitMarginINR": round(margin_gbp * GBP_TO_INR, 2),
                    "HybridScore": 0.45,
                    "ScoreBreakdown": {
                        "svd_latent_affinity": 0.45,
                        "collaborative_cross_sell": 0.45,
                        "margin_contribution": round(min(1.0, margin_gbp / 15.0), 3),
                        "category_affinity": 0.45,
                    },
                    "ExplanationBadge": "High-Velocity Staple",
                    "Explanation": "Bestselling staple recommended for guest / cold-start sessions.",
                })
                if len(recs) >= top_n:
                    break

        return recs

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns recommender health metrics and architecture telemetry."""
        self.ensure_ready()
        n_items = len(self.unique_items)
        n_users = len(self.unique_customers)

        # Calculate category breakdown
        cat_counts: Dict[str, int] = {}
        for sku, meta in self.product_catalog.items():
            c = meta.get("Category", "Gifts & General Merchandise")
            cat_counts[c] = cat_counts.get(c, 0) + 1

        avg_margin = float(np.mean([
            m.get("GrossMarginRate", 0.42) for m in self.product_catalog.values()
        ]))

        return {
            "status": "healthy",
            "model_architecture": "Hybrid SVD Matrix Factorization + Item-Item CF + Margin Optimizer",
            "svd_latent_dimensions": self.n_svd_components,
            "explained_variance_pct": round(self.explained_variance_ratio * 100.0, 2),
            "catalog_skus_indexed": n_items,
            "customer_profiles_indexed": n_users,
            "total_catalog_size": len(self.product_catalog),
            "supported_objectives": list(OBJECTIVE_WEIGHTS.keys()),
            "avg_catalog_margin_pct": round(avg_margin * 100.0, 1),
            "category_distribution": cat_counts,
            "currency_pair": "GBP / INR (1 GBP = 105 INR)",
            "trained_at": self.svd_trained_at or "precomputed",
        }

    # -------------------------------------------------------------------------
    # Helper Utilities
    # -------------------------------------------------------------------------

    def _get_item_metadata(self, sku: str) -> Dict[str, Any]:
        """Resolves SKU metadata with fallback defaults."""
        sku = str(sku).strip().upper()
        if sku in self.product_catalog:
            return self.product_catalog[sku]

        # Dynamic fallback
        desc = "Catalog Merchandise"
        cat, rate = categorize_product_desc(desc)
        return {
            "StockCode": sku,
            "Description": desc,
            "UnitPrice": 2.50,
            "UnitPriceGBP": 2.50,
            "UnitPriceINR": 262.50,
            "Category": cat,
            "GrossMarginRate": rate,
            "EstimatedUnitMarginGBP": round(2.50 * rate, 2),
            "EstimatedUnitMarginINR": round(2.50 * rate * GBP_TO_INR, 2),
            "TotalOrders": 1,
        }

    def _explain_badge(
        self,
        s_svd: float,
        s_cf: float,
        s_margin: float,
        s_cat: float,
        category: str,
        objective: str,
    ) -> Tuple[str, str]:
        """Constructs human-interpretable explanation tags."""
        if objective == "margin_max" and s_margin > 0.45:
            return "High-Margin Up-Sell", f"Accretive profit driver in {category} with superior gross margin."

        max_comp = max(s_svd, s_cf, s_margin, s_cat)
        if max_comp == s_margin and s_margin > 0.6:
            return "Profit-Accretive Up-Sell", f"Top unit margin contribution in {category}."
        if max_comp == s_cf and s_cf > 0.5:
            return "Frequent Cross-Sell Companion", "Strong co-purchase affinity with prior basket items."
        if max_comp == s_cat and s_cat > 0.4:
            return "Preferred Category Pick", f"Directly aligns with customer's high interest in {category}."
        if max_comp == s_svd and s_svd > 0.6:
            return "Latent Persona Match", "High mathematical affinity in 20-dimensional customer latent space."

        return "Personalized Best-Match", f"Multi-objective harmony across {category}."


# Process-wide singleton
_RECOMMENDER_SINGLETON: Optional[ProductRecommender] = None


def get_product_recommender(force_retrain: bool = False) -> ProductRecommender:
    """Returns initialized singleton ProductRecommender."""
    global _RECOMMENDER_SINGLETON
    if _RECOMMENDER_SINGLETON is None or force_retrain:
        rec = ProductRecommender()
        rec.ensure_ready()
        _RECOMMENDER_SINGLETON = rec
    return _RECOMMENDER_SINGLETON


if __name__ == "__main__":
    recommender = get_product_recommender()
    diag = recommender.get_diagnostics()
    print("\n--- RECOMMENDER DIAGNOSTICS ---")
    print(json.dumps(diag, indent=2))

    # Test Customer 17850
    cid = "17850"
    print(f"\n--- NEXT-BEST-SKUS FOR CUSTOMER {cid} (BALANCED) ---")
    recs = recommender.recommend_next_best_skus(cid, top_n=5, objective="balanced")
    for r in recs:
        print(f"  {r['Rank']}. [{r['StockCode']}] {r['Description']} (₹{r['UnitPriceINR']}) | {r['ExplanationBadge']} | Score: {r['HybridScore']}")

    # Test Customer 17850 with Margin-Max
    print(f"\n--- NEXT-BEST-SKUS FOR CUSTOMER {cid} (MARGIN-MAX) ---")
    margin_recs = recommender.recommend_next_best_skus(cid, top_n=5, objective="margin_max")
    for r in margin_recs:
        print(f"  {r['Rank']}. [{r['StockCode']}] {r['Description']} (₹{r['UnitPriceINR']}, Margin: ₹{r['EstimatedUnitMarginINR']}) | {r['ExplanationBadge']}")
