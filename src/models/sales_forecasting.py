"""
E-Commerce Sales Prediction & Demand Forecasting Engine.

Trains and benchmarks multiple regression models (Linear Regression,
Random Forest, XGBoost) using strict chronological train/test splits,
evaluates out-of-sample accuracy, and outputs production forecast artifacts.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

PROCESSED_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
FEATURES_PATH = PROCESSED_DATA_DIR / "daily_sales_features.csv"


class SalesForecastingPipeline:
    """
    Time-Series ML Pipeline:
    1. Temporal validation split (80% train, 20% out-of-sample test).
    2. Model training & comparison (Linear Regression, Random Forest, XGBoost).
    3. Metrics: MAE, RMSE, MAPE, R2.
    4. Feature importance extraction.
    5. Serialization of best model.
    """

    FEATURE_COLS = [
        "DayOfWeek", "DayOfMonth", "Month", "Quarter", "IsWeekend",
        "Lag_1", "Lag_2", "Lag_7", "Lag_14", "Lag_30",
        "RollingMean_7", "RollingStd_7", "RollingMean_14", "RollingMean_30",
        "LagOrders_1", "LagOrders_7"
    ]
    TARGET_COL = "DailyRevenue"

    def __init__(self, data_path: Path = FEATURES_PATH, test_size: float = 0.20):
        self.data_path = data_path
        self.test_size = test_size
        self.df: pd.DataFrame = None
        self.X_train: pd.DataFrame = None
        self.X_test: pd.DataFrame = None
        self.y_train: pd.Series = None
        self.y_test: pd.Series = None
        self.test_dates: pd.Series = None
        self.models = {}
        self.results = {}
        self.best_model_name: str = None
        self.best_model = None

    def load_and_split(self):
        """Loads data and performs strict chronological split (no shuffling)."""
        if not self.data_path.exists():
            from src.features.sales_features import SalesFeatureEngineer
            fe = SalesFeatureEngineer()
            self.df = fe.engineer_time_series_features()
        else:
            self.df = pd.read_csv(self.data_path, parse_dates=["Date"])

        # Temporal split index
        split_idx = int(len(self.df) * (1 - self.test_size))

        train_df = self.df.iloc[:split_idx].copy()
        test_df = self.df.iloc[split_idx:].copy()

        self.X_train = train_df[self.FEATURE_COLS]
        self.y_train = train_df[self.TARGET_COL]

        self.X_test = test_df[self.FEATURE_COLS]
        self.y_test = test_df[self.TARGET_COL]
        self.test_dates = test_df["Date"]

        print(f"[SalesForecaster] Chronological Split:")
        print(f"  • Training: {len(train_df)} days ({train_df['Date'].min().date()} to {train_df['Date'].max().date()})")
        print(f"  • Testing:  {len(test_df)} days ({test_df['Date'].min().date()} to {test_df['Date'].max().date()})")

    def train_and_evaluate(self) -> pd.DataFrame:
        """Trains candidate models and calculates out-of-sample metrics."""
        if self.X_train is None:
            self.load_and_split()

        self.models = {
            "Linear Regression (Baseline)": LinearRegression(),
            "Random Forest Regressor": RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42),
            "XGBoost Regressor": XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=4, subsample=0.8, random_state=42)
        }

        eval_records = []
        predictions_dict = {"Date": self.test_dates, "ActualRevenue": self.y_test}

        for name, model in self.models.items():
            model.fit(self.X_train, self.y_train)
            preds = model.predict(self.X_test)
            # Ensure non-negative revenue predictions
            preds = np.clip(preds, 0, None)
            predictions_dict[f"Pred_{name}"] = preds

            mae = mean_absolute_error(self.y_test, preds)
            rmse = np.sqrt(mean_squared_error(self.y_test, preds))
            r2 = r2_score(self.y_test, preds)
            # Safe MAPE (avoid division by zero on zero-trading days)
            non_zero_mask = self.y_test > 0
            mape = np.mean(np.abs((self.y_test[non_zero_mask] - preds[non_zero_mask]) / self.y_test[non_zero_mask])) * 100

            eval_records.append({
                "Model": name,
                "MAE (£)": round(mae, 2),
                "RMSE (£)": round(rmse, 2),
                "MAPE (%)": round(mape, 2),
                "R2_Score": round(r2, 4)
            })

        eval_df = pd.DataFrame(eval_records).sort_values(by="RMSE (£)")

        # Select Best Model based on Lowest RMSE
        best_row = eval_df.iloc[0]
        self.best_model_name = best_row["Model"]
        self.best_model = self.models[self.best_model_name]

        # Save predictions dataframe for dashboard visualization
        preds_df = pd.DataFrame(predictions_dict)
        preds_path = PROCESSED_DATA_DIR / "sales_forecast_results.csv"
        preds_df.to_csv(preds_path, index=False)
        print(f"[SalesForecaster] Saved evaluation predictions to: {preds_path}")

        # Save best model binary
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        best_model_path = MODELS_DIR / "best_sales_forecaster.joblib"
        joblib.dump(self.best_model, best_model_path)
        print(f"[SalesForecaster] Serialized Best Model ({self.best_model_name}) to: {best_model_path}")

        return eval_df

    def get_feature_importance(self) -> pd.DataFrame:
        """Extracts top predictive signals from the tree-based model."""
        if hasattr(self.best_model, "feature_importances_"):
            importances = self.best_model.feature_importances_
        else:
            rf = self.models["Random Forest Regressor"]
            importances = rf.feature_importances_

        feat_df = pd.DataFrame({
            "Feature": self.FEATURE_COLS,
            "Importance": importances
        }).sort_values(by="Importance", ascending=False).reset_index(drop=True)

        return feat_df


if __name__ == "__main__":
    pipeline = SalesForecastingPipeline()
    pipeline.load_and_split()
    print("\n--- MODEL PERFORMANCE COMPARISON (OUT-OF-SAMPLE TEST SET) ---")
    eval_table = pipeline.train_and_evaluate()
    print(eval_table.to_string(index=False))

    print(f"\n--- TOP PREDICTIVE SIGNALS (BEST MODEL: {pipeline.best_model_name}) ---")
    feat_imp = pipeline.get_feature_importance()
    print(feat_imp.head(8).to_string(index=False))
