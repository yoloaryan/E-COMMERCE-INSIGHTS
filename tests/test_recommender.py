"""
Unit Tests for Product Recommendation Engine & Cold-Start Fallback.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys
import joblib

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.models.recommender import ProductRecommender

MODELS_DIR = ROOT_DIR / "models"


def test_recommender_model_artifacts():
    """Asserts similarity matrix and catalog are loadable and aligned."""
    sim_path = MODELS_DIR / "item_similarity_matrix.joblib"
    cat_path = MODELS_DIR / "product_catalog.joblib"

    assert sim_path.exists(), "Similarity matrix artifact missing"
    assert cat_path.exists(), "Product catalog artifact missing"

    sim = joblib.load(sim_path)
    cat = joblib.load(cat_path)

    assert isinstance(sim, pd.DataFrame)
    assert len(sim) > 1000
    assert len(cat) > 1000


def test_item_recommendation_and_cold_start():
    """Tests item-to-item recommendations and fallback behavior."""
    sim_path = MODELS_DIR / "item_similarity_matrix.joblib"
    cat_path = MODELS_DIR / "product_catalog.joblib"

    sim = joblib.load(sim_path)
    cat = joblib.load(cat_path)

    recommender = ProductRecommender()
    recommender.similarity_df = sim
    recommender.product_catalog = cat
    recommender.popularity_ranking = list(cat.keys())[:20]

    # Test real item: 22423 (Regency Cakestand)
    recs = recommender.recommend_similar_items("22423", top_n=5)
    assert len(recs) == 5
    for item in recs:
        assert "StockCode" in item
        assert "Description" in item
        assert "SimilarityScore" in item
        assert item["StockCode"] != "22423"  # Must not recommend itself

    # Test unknown SKU (Cold-Start Fallback)
    cold_recs = recommender.recommend_similar_items("UNKNOWN_NONEXISTENT_SKU", top_n=3)
    assert len(cold_recs) == 3
    for item in cold_recs:
        assert "StockCode" in item

