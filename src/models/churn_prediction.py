"""
Customer Churn Prediction Engine.

Trains and benchmarks multiple classification algorithms (Logistic Regression,
Random Forest, XGBoost) to predict customer churn probability, identify
high-risk accounts, and output actionable retention recommendations.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report
)
import joblib

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
CHURN_FEATURES_PATH = PROCESSED_DATA_DIR / "customer_churn_features.csv"


class CustomerChurnPredictor:
    """
    Churn Modeling Pipeline:
    1. Stratified Train-Test Splitting (80/20).
    2. Standardization for linear model & tree ensemble benchmarks.
    3. Metrics: Accuracy, Precision, Recall, F1-Score, ROC-AUC.
    4. Risk Tier Scoring (Low, Medium, High).
    5. High-Value At-Risk Identification for proactive customer retention.
    """

    FEATURE_COLS = [
        "Recency", "HistoricalFrequency", "HistoricalMonetary", "HistoricalUnits",
        "UniqueSKUs", "Tenure", "AOV", "UnitsPerOrder", "PurchaseVelocity"
    ]
    TARGET_COL = "Churn"

    def __init__(self, data_path: Path = CHURN_FEATURES_PATH, test_size: float = 0.20, random_state: int = 42):
        self.data_path = data_path
        self.test_size = test_size
        self.random_state = random_state
        self.df: pd.DataFrame = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.scaler = StandardScaler()
        self.models = {}
        self.best_model_name: str = None
        self.best_model = None

    def load_and_split(self):
        if not self.data_path.exists():
            from src.features.churn_features import ChurnFeatureEngineer
            fe = ChurnFeatureEngineer()
            self.df = fe.engineer_churn_features()
        else:
            self.df = pd.read_csv(self.data_path)

        X = self.df[self.FEATURE_COLS]
        y = self.df[self.TARGET_COL]

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=self.test_size, stratify=y, random_state=self.random_state
        )

        print(f"[Churn] Stratified Split: Train={len(self.X_train)} samples, Test={len(self.X_test)} samples.")
        print(f"[Churn] Target Balance: {y.value_counts(normalize=True).round(3).to_dict()}")

    def train_and_evaluate(self) -> pd.DataFrame:
        """Trains competitive classifiers and computes comprehensive validation metrics."""
        if self.X_train is None:
            self.load_and_split()

        # Scaled features for Logistic Regression
        X_train_scaled = self.scaler.fit_transform(self.X_train)
        X_test_scaled = self.scaler.transform(self.X_test)

        # Calculate positive scale weight for XGBoost
        neg_count = (self.y_train == 0).sum()
        pos_count = (self.y_train == 1).sum()
        scale_weight = neg_count / pos_count if pos_count > 0 else 1.0

        self.models = {
            "Logistic Regression": {
                "model": LogisticRegression(class_weight="balanced", max_iter=1000, random_state=self.random_state),
                "is_scaled": True
            },
            "Random Forest Classifier": {
                "model": RandomForestClassifier(n_estimators=100, max_depth=6, class_weight="balanced", random_state=self.random_state),
                "is_scaled": False
            },
            "XGBoost Classifier": {
                "model": XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, scale_pos_weight=scale_weight, eval_metric="logloss", random_state=self.random_state),
                "is_scaled": False
            }
        }

        eval_records = []
        for name, config in self.models.items():
            clf = config["model"]
            X_tr = X_train_scaled if config["is_scaled"] else self.X_train
            X_te = X_test_scaled if config["is_scaled"] else self.X_test

            clf.fit(X_tr, self.y_train)
            y_pred = clf.predict(X_te)
            y_prob = clf.predict_proba(X_te)[:, 1]

            acc = accuracy_score(self.y_test, y_pred)
            prec = precision_score(self.y_test, y_pred)
            rec = recall_score(self.y_test, y_pred)
            f1 = f1_score(self.y_test, y_pred)
            roc_auc = roc_auc_score(self.y_test, y_prob)

            eval_records.append({
                "Model": name,
                "Accuracy": round(acc, 4),
                "Precision": round(prec, 4),
                "Recall": round(rec, 4),
                "F1_Score": round(f1, 4),
                "ROC_AUC": round(roc_auc, 4)
            })

        eval_df = pd.DataFrame(eval_records).sort_values(by="ROC_AUC", ascending=False).reset_index(drop=True)

        # Select Best Model based on ROC-AUC
        self.best_model_name = eval_df.iloc[0]["Model"]
        self.best_model = self.models[self.best_model_name]["model"]

        # Serialize Best Model
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_out = MODELS_DIR / "best_churn_classifier.joblib"
        scaler_out = MODELS_DIR / "churn_scaler.joblib"
        joblib.dump(self.best_model, model_out)
        joblib.dump(self.scaler, scaler_out)
        print(f"[Churn] Serialized Best Model ({self.best_model_name}) to: {model_out}")

        return eval_df

    def score_all_customers(self) -> pd.DataFrame:
        """
        Calculates individual Churn Risk Probabilities for all historical customers,
        assigns risk tiers, and highlights High-Value At-Risk VIP accounts.
        """
        if self.best_model is None:
            self.train_and_evaluate()

        df_scored = self.df.copy()
        is_scaled = self.models[self.best_model_name]["is_scaled"]
        X_all = self.scaler.transform(df_scored[self.FEATURE_COLS]) if is_scaled else df_scored[self.FEATURE_COLS]

        churn_probs = self.best_model.predict_proba(X_all)[:, 1]
        df_scored["Churn_Probability"] = np.round(churn_probs, 4)

        # Risk Tiers
        conditions = [
            df_scored["Churn_Probability"] >= 0.70,
            (df_scored["Churn_Probability"] >= 0.35) & (df_scored["Churn_Probability"] < 0.70),
            df_scored["Churn_Probability"] < 0.35
        ]
        tier_names = ["High Risk", "Medium Risk", "Low Risk"]
        df_scored["Churn_Risk_Tier"] = np.select(conditions, tier_names, default="Low Risk")

        # Action Recommendations
        def recommend_action(row):
            prob = row["Churn_Probability"]
            spend = row["HistoricalMonetary"]
            if prob >= 0.70 and spend >= 1000:
                return "CRITICAL INTERVENTION: Assign dedicated account manager; direct phone outreach; bespoke VIP discount."
            elif prob >= 0.70:
                return "AUTOMATED WIN-BACK: Automated 3-part email campaign offering 20% off favorite catalog category."
            elif prob >= 0.35:
                return "RE-ENGAGEMENT: Cross-sell recommendation newsletter highlighting new arrivals in past purchased SKUs."
            else:
                return "LOYALTY PRESERVATION: Standard promotional cadence and loyalty rewards points."

        df_scored["Retention_Strategy"] = df_scored.apply(recommend_action, axis=1)

        # Save predictions dataset
        preds_path = PROCESSED_DATA_DIR / "customer_churn_predictions.csv"
        df_scored.to_csv(preds_path, index=False)
        print(f"[Churn] Saved full cohort churn risk scoring to: {preds_path}")

        return df_scored

    def get_feature_importance(self) -> pd.DataFrame:
        """Extracts normalized feature importance from best tree-based model."""
        if hasattr(self.best_model, "feature_importances_"):
            importances = self.best_model.feature_importances_
        else:
            rf = self.models["Random Forest Classifier"]["model"]
            importances = rf.feature_importances_

        feat_df = pd.DataFrame({
            "Feature": self.FEATURE_COLS,
            "Importance": importances
        }).sort_values(by="Importance", ascending=False).reset_index(drop=True)
        return feat_df

    def explain_customer_risk(self, customer_ids: list = None, top_k_features: int = 5) -> pd.DataFrame:
        """
        Uses SHAP (SHapley Additive exPlanations) to explain individual customer churn risk scores.
        Identifies the exact behavioral drivers pushing a customer toward churning or staying.
        """
        import shap

        if self.best_model is None:
            self.train_and_evaluate()

        # Target tree model for exact TreeExplainer
        tree_model = self.best_model if hasattr(self.best_model, "feature_importances_") else self.models["Random Forest Classifier"]["model"]
        explainer = shap.TreeExplainer(tree_model)

        df_target = self.df.copy()
        if customer_ids is not None:
            df_target = df_target[df_target["CustomerID"].astype(str).isin([str(c) for c in customer_ids])].copy()

        if len(df_target) == 0:
            return pd.DataFrame()

        X_target = df_target[self.FEATURE_COLS]
        shap_values = explainer.shap_values(X_target)

        # For binary classification with scikit-learn/xgboost, extract positive class (Churn=1)
        if isinstance(shap_values, list) and len(shap_values) == 2:
            shap_churn = shap_values[1]
        elif len(shap_values.shape) == 3 and shap_values.shape[-1] == 2:
            shap_churn = shap_values[:, :, 1]
        else:
            shap_churn = shap_values

        explanations = []
        for idx, (_, row) in enumerate(df_target.iterrows()):
            c_shap = shap_churn[idx]
            feature_impacts = sorted(
                zip(self.FEATURE_COLS, row[self.FEATURE_COLS], c_shap),
                key=lambda x: abs(x[2]),
                reverse=True
            )
            top_drivers = [
                f"{feat} ({val:.1f}): {'+' if impact > 0 else ''}{impact:.3f} SHAP"
                for feat, val, impact in feature_impacts[:top_k_features]
            ]
            explanations.append({
                "CustomerID": row["CustomerID"],
                "HistoricalMonetary": round(row["HistoricalMonetary"], 2),
                "Top_Risk_Drivers": "; ".join(top_drivers),
                "Primary_Risk_Driver": feature_impacts[0][0],
                "Primary_Driver_Direction": "Increases Churn" if feature_impacts[0][2] > 0 else "Reduces Churn"
            })

        return pd.DataFrame(explanations)


if __name__ == "__main__":
    predictor = CustomerChurnPredictor()
    predictor.load_and_split()
    print("\n--- CHURN CLASSIFIER BENCHMARK (TEST SET EVALUATION) ---")
    eval_table = predictor.train_and_evaluate()
    print(eval_table.to_string(index=False))

    print(f"\n--- FEATURE IMPORTANCES ({predictor.best_model_name}) ---")
    feat_imp = predictor.get_feature_importance()
    print(feat_imp.to_string(index=False))

    print("\n--- GENERATING CUSTOMER RISK SCORES & INTERVENTION PLAYBOOK ---")
    scored = predictor.score_all_customers()
    tier_counts = scored["Churn_Risk_Tier"].value_counts()
    print("\nCustomer Distribution across Risk Tiers:")
    for tier, cnt in tier_counts.items():
        pct = (cnt / len(scored)) * 100
        print(f"  • {tier:12s}: {cnt:,} customers ({pct:.1f}%)")

    high_value_at_risk = scored[
        (scored["Churn_Risk_Tier"] == "High Risk") & (scored["HistoricalMonetary"] >= 1000)
    ]
    print(f"\nCRITICAL VIP ACCOUNTS AT RISK OF CHURNING: {len(high_value_at_risk):,} accounts.")
    print(f"Total Revenue Exposure from At-Risk VIPs: £{high_value_at_risk['HistoricalMonetary'].sum():,.2f}")
