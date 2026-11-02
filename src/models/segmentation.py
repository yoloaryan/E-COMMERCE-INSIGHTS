"""
Customer Segmentation Model using K-Means Clustering & RFM Analysis.

Applies log-transformation to handle power-law spend distributions,
standardizes feature scales, selects optimal K via Elbow & Silhouette metrics,
and maps clusters to actionable business customer personas.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import joblib

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


class CustomerSegmentationModel:
    """
    Industry-Standard RFM K-Means Segmentation Engine:
    1. Log-transformation: Resolves severe right-skew in financial transactions.
    2. Z-Score Standardization: Equilibrates feature weights for Euclidean distance.
    3. Optimal K Evaluation: Evaluates WCSS (Inertia) and Silhouette Scores across K in [2, 8].
    4. Business Persona Profiling: Maps clusters to actionable retention and marketing strategies.
    """

    FEATURES = ["Recency", "Frequency", "Monetary"]

    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.kmeans = KMeans(
            n_clusters=n_clusters,
            init="k-means++",
            n_init=15,
            max_iter=300,
            random_state=random_state
        )
        self.rfm_df: pd.DataFrame = None
        self.scaled_features: np.ndarray = None
        self.segmented_df: pd.DataFrame = None
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

    def prepare_features(self, rfm_df: pd.DataFrame) -> np.ndarray:
        """
        Applies mathematical log1p transformation followed by Z-Score scaling.
        """
        self.rfm_df = rfm_df.copy()

        # Handle skewness with natural log transformation (log(1 + x))
        log_transformed = np.log1p(self.rfm_df[self.FEATURES])

        # Standardize: mean=0, std=1
        self.scaled_features = self.scaler.fit_transform(log_transformed)
        return self.scaled_features

    def evaluate_cluster_range(self, k_min: int = 2, k_max: int = 8) -> pd.DataFrame:
        """
        Computes Inertia (Elbow Method) and Silhouette Scores for a range of K.
        Assists data scientists in selecting mathematically defensible cluster counts.
        """
        if self.scaled_features is None:
            raise ValueError("Call prepare_features() before evaluating clusters.")

        results = []
        for k in range(k_min, k_max + 1):
            km = KMeans(n_clusters=k, init="k-means++", n_init=10, max_iter=300, random_state=self.random_state)
            labels = km.fit_predict(self.scaled_features)
            inertia = km.inertia_
            sil = silhouette_score(self.scaled_features, labels)
            results.append({
                "K": k,
                "Inertia_WCSS": round(inertia, 2),
                "Silhouette_Score": round(sil, 4)
            })

        eval_df = pd.DataFrame(results)
        return eval_df

    def fit_predict(self) -> pd.DataFrame:
        """
        Fits final K-Means model, assigns cluster IDs, and attaches business personas.
        """
        if self.scaled_features is None:
            raise ValueError("Features not prepared. Call prepare_features() first.")

        labels = self.kmeans.fit_predict(self.scaled_features)
        self.rfm_df["Cluster"] = labels

        # Profile clusters to dynamically map personas based on mean RFM characteristics
        cluster_summary = self.rfm_df.groupby("Cluster").agg(
            MeanRecency=("Recency", "mean"),
            MeanFrequency=("Frequency", "mean"),
            MeanMonetary=("Monetary", "mean"),
            Count=("CustomerID", "count")
        )

        # Dynamic persona mapping:
        # 1. Champions: Low Recency, Highest Monetary & Frequency
        # 2. Loyal: Low/Med Recency, Moderate-High Spend
        # 3. At Risk: High Recency, Moderate-High Historical Spend
        # 4. Hibernating/Occasional: High Recency, Low Spend, Low Frequency
        persona_map = {}
        for c in cluster_summary.index:
            r = cluster_summary.loc[c, "MeanRecency"]
            f = cluster_summary.loc[c, "MeanFrequency"]
            m = cluster_summary.loc[c, "MeanMonetary"]

            if f > cluster_summary["MeanFrequency"].median() and m > cluster_summary["MeanMonetary"].median() and r <= cluster_summary["MeanRecency"].median():
                persona_map[c] = "Champions (VIP)"
            elif r <= cluster_summary["MeanRecency"].median() and f >= 2:
                persona_map[c] = "Loyal Customers"
            elif r > cluster_summary["MeanRecency"].median() and m > cluster_summary["MeanMonetary"].median():
                persona_map[c] = "At-Risk / Lapsing"
            else:
                persona_map[c] = "Occasional / Hibernating"

        self.rfm_df["Segment_Name"] = self.rfm_df["Cluster"].map(persona_map)

        # Save artifacts
        model_path = MODELS_DIR / "kmeans_rfm_model.joblib"
        scaler_path = MODELS_DIR / "rfm_scaler.joblib"
        joblib.dump(self.kmeans, model_path)
        joblib.dump(self.scaler, scaler_path)
        print(f"[Segmentation] Serialized K-Means model to: {model_path}")
        print(f"[Segmentation] Serialized Scaler to: {scaler_path}")

        # Save segmented customer dataset
        output_csv = PROCESSED_DATA_DIR / "customer_segments.csv"
        self.rfm_df.to_csv(output_csv, index=False)
        print(f"[Segmentation] Saved segmented customer master to: {output_csv}")

        self.segmented_df = self.rfm_df
        return self.segmented_df

    def get_segment_playbook(self) -> pd.DataFrame:
        """
        Returns the business marketing playbook and financial contribution per persona.
        """
        playbook = self.segmented_df.groupby("Segment_Name").agg(
            CustomerCount=("CustomerID", "count"),
            AvgRecency_Days=("Recency", "mean"),
            AvgFrequency_Orders=("Frequency", "mean"),
            AvgMonetary_Spend=("Monetary", "mean"),
            TotalSegmentRevenue=("Monetary", "sum")
        ).round(2).reset_index()

        total_rev = playbook["TotalSegmentRevenue"].sum()
        playbook["Revenue_Contribution (%)"] = round((playbook["TotalSegmentRevenue"] / total_rev) * 100, 2)

        # Strategic Action Guide
        strategy_dict = {
            "Champions (VIP)": "Exclusive rewards, early product drops, dedicated account management. Do not spam with generic discounts.",
            "Loyal Customers": "Cross-sell high-affinity categories, loyalty tier accelerators, referral incentives.",
            "At-Risk / Lapsing": "Automated win-back email sequence, personalized 'We Miss You' discount on their favorite past items.",
            "Occasional / Hibernating": "Re-engagement promotions, low-price entry bundles, clearance marketing; avoid high ad spend."
        }
        playbook["Recommended_Strategy"] = playbook["Segment_Name"].map(strategy_dict)
        return playbook


if __name__ == "__main__":
    from src.features.rfm import RFMFeatureEngineer

    fe = RFMFeatureEngineer()
    rfm_data = fe.compute_rfm()
    fe.calculate_rfm_quintile_scores()

    seg_model = CustomerSegmentationModel(n_clusters=4)
    seg_model.prepare_features(rfm_data)

    print("\n--- ELBOW METHOD & SILHOUETTE SCORE ANALYSIS (K=2 to 8) ---")
    eval_table = seg_model.evaluate_cluster_range(2, 8)
    print(eval_table.to_string(index=False))

    print("\n--- FITTING FINAL K-MEANS MODEL (K=4) ---")
    seg_model.fit_predict()

    print("\n--- CUSTOMER SEGMENTATION BUSINESS PLAYBOOK ---")
    playbook = seg_model.get_segment_playbook()
    print(playbook[["Segment_Name", "CustomerCount", "AvgRecency_Days", "AvgFrequency_Orders", "AvgMonetary_Spend", "Revenue_Contribution (%)"]].to_string(index=False))
