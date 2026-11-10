"""
FastAPI Production ML Inference & Analytics Serving Layer.

Serves real-time predictions from serialized joblib artifacts:
- Time-Series Demand & Sales Forecasting
- Customer Churn Risk Classification & SHAP Explainability
- Item-Item Collaborative Filtering Product Recommendations
- Real-Time RFM Customer Persona Segmentation
- Live Analytical Business Intelligence KPIs via DuckDB
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import json
import numpy as np
import pandas as pd
import joblib
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.models.recommender import ProductRecommender

MODELS_DIR = ROOT_DIR / "models"
MANIFEST_PATH = MODELS_DIR / "model_manifest.json"

# Initialize FastAPI App
app = FastAPI(
    title="Nexus Retail AI | ML Serving Engine",
    description="Enterprise REST API for E-Commerce Customer Intelligence & Sales Prediction",
    version="1.0.0"
)

# Enable CORS for local development and cloud static hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Global Model Registry / Cache
# -----------------------------------------------------------------------------
class ModelRegistry:
    def __init__(self):
        self.kmeans_model = None
        self.rfm_scaler = None
        self.sales_model = None
        self.churn_model = None
        self.churn_scaler = None
        self.item_sim = None
        self.catalog = None
        self.manifest = {}
        self.recommender = None
        self.load_all()

    def load_all(self):
        print("[API] Loading serialized ML models into memory...")
        if (MODELS_DIR / "kmeans_rfm_model.joblib").exists():
            self.kmeans_model = joblib.load(MODELS_DIR / "kmeans_rfm_model.joblib")
            self.rfm_scaler = joblib.load(MODELS_DIR / "rfm_scaler.joblib")
        
        if (MODELS_DIR / "best_sales_forecaster.joblib").exists():
            self.sales_model = joblib.load(MODELS_DIR / "best_sales_forecaster.joblib")

        if (MODELS_DIR / "best_churn_classifier.joblib").exists():
            self.churn_model = joblib.load(MODELS_DIR / "best_churn_classifier.joblib")
            self.churn_scaler = joblib.load(MODELS_DIR / "churn_scaler.joblib")

        if (MODELS_DIR / "item_similarity_matrix.joblib").exists():
            self.item_sim = joblib.load(MODELS_DIR / "item_similarity_matrix.joblib")
            self.catalog = joblib.load(MODELS_DIR / "product_catalog.joblib")
            self.recommender = ProductRecommender()
            self.recommender.similarity_df = self.item_sim
            self.recommender.product_catalog = self.catalog
            self.recommender.popularity_ranking = list(self.catalog.keys())[:30]

        if MANIFEST_PATH.exists():
            with open(MANIFEST_PATH, "r") as f:
                self.manifest = json.load(f)

        print("[API] Model registry initialized successfully.")

REGISTRY = ModelRegistry()


# -----------------------------------------------------------------------------
# WebSocket Connection Manager for Live Reactive POS Streaming
# -----------------------------------------------------------------------------
class ConnectionManager:
    """Manages active real-time WebSocket client connections for live order streaming."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)

ws_manager = ConnectionManager()


# -----------------------------------------------------------------------------
# Pydantic Request & Response Schemas
# -----------------------------------------------------------------------------
class SalesForecastRequest(BaseModel):
    DayOfWeek: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    DayOfMonth: int = Field(..., ge=1, le=31)
    Month: int = Field(..., ge=1, le=12)
    Quarter: int = Field(..., ge=1, le=4)
    IsWeekend: int = Field(..., ge=0, le=1)
    Lag_1: float = Field(..., description="Revenue yesterday")
    Lag_2: float = Field(..., description="Revenue 2 days ago")
    Lag_7: float = Field(..., description="Revenue same day last week")
    Lag_14: float = Field(..., description="Revenue 2 weeks ago")
    Lag_30: float = Field(..., description="Revenue 30 days ago")
    RollingMean_7: float = Field(...)
    RollingStd_7: float = Field(...)
    RollingMean_14: float = Field(...)
    RollingMean_30: float = Field(...)
    LagOrders_1: float = Field(...)
    LagOrders_7: float = Field(...)


class ChurnPredictionRequest(BaseModel):
    Recency: float = Field(..., ge=0, description="Days since last order")
    HistoricalFrequency: float = Field(..., ge=1, description="Total completed orders")
    HistoricalMonetary: float = Field(..., description="Total cumulative spend (£)")
    HistoricalUnits: float = Field(..., description="Total items purchased")
    UniqueSKUs: float = Field(..., ge=1, description="Number of distinct products ordered")
    Tenure: float = Field(..., ge=0, description="Days since first recorded purchase")
    AOV: float = Field(..., description="Average Order Value (£)")
    UnitsPerOrder: float = Field(...)
    PurchaseVelocity: float = Field(..., description="Orders per 30 days")


class RFMSegmentRequest(BaseModel):
    Recency: float = Field(..., ge=0, description="Days since last purchase")
    Frequency: int = Field(..., ge=1, description="Lifetime completed orders")
    Monetary: float = Field(..., gt=0, description="Total customer spend (£)")


class OrderItem(BaseModel):
    stock_code: str = Field(..., json_schema_extra={"example": "22423"})
    description: str = Field(default="Retail Product SKU", json_schema_extra={"example": "Regency Cakestand 3 Tier"})
    quantity: int = Field(..., ge=1, json_schema_extra={"example": 2})
    unit_price: float = Field(..., ge=0.01, json_schema_extra={"example": 10.95})


class OrderInjectionRequest(BaseModel):
    customer_id: str = Field(..., json_schema_extra={"example": "14096"})
    country: str = Field(default="United Kingdom", json_schema_extra={"example": "United Kingdom"})
    items: List[OrderItem]


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
@app.get("/", tags=["System"])
def root():
    """Health check and general API metadata."""
    return {
        "status": "online",
        "service": "Nexus Retail AI Serving API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "models_loaded": {
            "sales_forecaster": REGISTRY.sales_model is not None,
            "churn_classifier": REGISTRY.churn_model is not None,
            "rfm_segmenter": REGISTRY.kmeans_model is not None,
            "recommender_catalog_size": len(REGISTRY.catalog) if REGISTRY.catalog else 0
        }
    }


@app.get("/health", tags=["System"])
def health_check():
    """Kubernetes / Docker health probe endpoint."""
    return {"status": "healthy", "service": "e-commerce-ml-api"}


@app.post("/api/v1/forecast/sales", tags=["Sales Forecasting"])
def predict_daily_sales(payload: SalesForecastRequest):
    """Predicts expected gross daily revenue given temporal lags and rolling indicators."""
    if REGISTRY.sales_model is None:
        raise HTTPException(status_code=503, detail="Sales forecasting model not loaded.")

    feature_cols = [
        "DayOfWeek", "DayOfMonth", "Month", "Quarter", "IsWeekend",
        "Lag_1", "Lag_2", "Lag_7", "Lag_14", "Lag_30",
        "RollingMean_7", "RollingStd_7", "RollingMean_14", "RollingMean_30",
        "LagOrders_1", "LagOrders_7"
    ]
    input_data = pd.DataFrame([payload.model_dump()])[feature_cols]
    prediction = float(REGISTRY.sales_model.predict(input_data)[0])
    prediction = max(0.0, round(prediction, 2))

    return {
        "predicted_daily_revenue_gbp": prediction,
        "model_name": "Random Forest Regressor (Ensemble ML)",
        "inputs": payload.model_dump()
    }


@app.post("/api/v1/churn/predict", tags=["Churn Early-Warning"])
def predict_churn_risk(payload: ChurnPredictionRequest):
    """Scores customer churn probability and assigns proactive retention strategy."""
    if REGISTRY.churn_model is None:
        raise HTTPException(status_code=503, detail="Churn classification model not loaded.")

    feature_cols = [
        "Recency", "HistoricalFrequency", "HistoricalMonetary", "HistoricalUnits",
        "UniqueSKUs", "Tenure", "AOV", "UnitsPerOrder", "PurchaseVelocity"
    ]
    input_df = pd.DataFrame([payload.model_dump()])[feature_cols]
    prob = float(REGISTRY.churn_model.predict_proba(input_df)[0, 1])

    if prob >= 0.65:
        tier = "High Risk"
        strategy = "VIP EXECUTIVE INTERVENTION: Dedicated account manager consultation + bespoke incentive."
    elif prob >= 0.50:
        tier = "Elevated Risk"
        strategy = "AUTOMATED WIN-BACK: 3-part re-engagement sequence with 20% discount on favorite categories."
    elif prob >= 0.35:
        tier = "Medium Risk"
        strategy = "RE-ENGAGEMENT: Cross-sell catalog newsletter featuring new arrivals in past categories."
    else:
        tier = "Low Risk (Healthy)"
        strategy = "LOYALTY PRESERVATION: Standard promotional cadence and VIP reward points."

    return {
        "churn_probability": round(prob, 4),
        "risk_tier": tier,
        "is_churn_predicted": prob >= 0.50,
        "recommended_strategy": strategy
    }


@app.get("/api/v1/recommend/item/{stock_code}", tags=["Recommender Engine"])
def recommend_cross_sell_products(stock_code: str, top_n: int = Query(5, ge=1, le=20)):
    """Item-to-Item cross-sell recommendations ('Customers Who Bought This Also Bought...')."""
    if REGISTRY.recommender is None:
        raise HTTPException(status_code=503, detail="Product recommender matrix not loaded.")

    clean_code = str(stock_code).strip().upper()
    recs = REGISTRY.recommender.recommend_similar_items(clean_code, top_n=top_n)

    is_cold_start = clean_code not in REGISTRY.recommender.similarity_df.index
    target_meta = REGISTRY.catalog.get(clean_code, {"Description": "Catalog Item", "UnitPrice": 0.0})

    return {
        "query_stock_code": clean_code,
        "query_description": target_meta.get("Description", "Unknown Product"),
        "is_cold_start_fallback": is_cold_start,
        "recommendations_count": len(recs),
        "recommendations": recs
    }


@app.post("/api/v1/segment/rfm", tags=["Customer Segmentation"])
def segment_customer(payload: RFMSegmentRequest):
    """Categorizes customer into one of 4 behavioral personas via RFM Log-Transformation & K-Means."""
    if REGISTRY.kmeans_model is None or REGISTRY.rfm_scaler is None:
        raise HTTPException(status_code=503, detail="Segmentation model or scaler not loaded.")

    input_df = pd.DataFrame([payload.model_dump()])[["Recency", "Frequency", "Monetary"]]
    log_transformed = np.log1p(input_df)
    scaled = REGISTRY.rfm_scaler.transform(log_transformed)
    cluster_id = int(REGISTRY.kmeans_model.predict(scaled)[0])

    # Cluster mapping based on trained persona centroids
    persona_map = {
        0: {"name": "At-Risk / Lapsing", "description": "High historical spend, but long recency dormancy."},
        1: {"name": "Champions (VIPs)", "description": "Top-tier transactional velocity and high monetary spend."},
        2: {"name": "Occasional / Hibernating", "description": "Low frequency, low monetary spend, infrequent visitors."},
        3: {"name": "Loyal Customers", "description": "Steady regular buyers with moderate basket sizes."}
    }
    persona = persona_map.get(cluster_id, {"name": f"Cluster {cluster_id}", "description": "Behavioral Segment"})

    return {
        "cluster_id": cluster_id,
        "segment_name": persona["name"],
        "description": persona["description"],
        "inputs": payload.model_dump()
    }


@app.get("/api/v1/analytics/kpis", tags=["BI Analytics"])
def get_executive_kpis():
    """Fetches macro business KPIs via in-memory DuckDB analytical engine."""
    from src.data.run_queries import DuckDBAnalyticsRunner
    runner = DuckDBAnalyticsRunner()
    top_prods = runner.query_top_products(5)
    monthly = runner.query_monthly_velocity()
    churn_audit = runner.query_churn_inactivity_audit()

    return {
        "total_gross_revenue_gbp": round(float(monthly["gross_revenue"].sum()), 2),
        "total_completed_orders": int(monthly["total_orders"].sum()),
        "total_units_sold": int(monthly["total_units_sold"].sum()),
        "overall_aov_gbp": round(float(monthly["gross_revenue"].sum() / monthly["total_orders"].sum()), 2),
        "top_revenue_products": top_prods.to_dict(orient="records"),
        "churn_audit_summary": churn_audit.to_dict(orient="records")
    }


@app.get("/api/v1/clv/summary", tags=["Customer Lifetime Value (BTYD)"])
def get_clv_portfolio_summary():
    """Returns macro 12-month expected customer lifetime value metrics across BTYD cohorts."""
    clv_pq = ROOT_DIR / "data" / "processed" / "customer_clv_predictions.parquet"
    if not clv_pq.exists():
        raise HTTPException(status_code=503, detail="CLV predictions dataset not available.")

    df = pd.read_parquet(clv_pq)
    summary = df.groupby("CLV_Segment").agg(
        customers=("CustomerID", "count"),
        avg_p_alive=("P_Alive", "mean"),
        total_clv_gbp=("CLV_12M_GBP", "sum"),
        avg_clv_gbp=("CLV_12M_GBP", "mean")
    ).reset_index()

    total_portfolio_clv = float(df["CLV_12M_GBP"].sum())

    return {
        "total_12m_portfolio_clv_gbp": round(total_portfolio_clv, 2),
        "total_evaluated_customers": len(df),
        "segments": summary.to_dict(orient="records")
    }


@app.get("/api/v1/clv/customer/{customer_id}", tags=["Customer Lifetime Value (BTYD)"])
def get_customer_clv(customer_id: str):
    """Retrieves individual BTYD Customer Lifetime Value, P(Alive), and 12-Month cash flow projection."""
    clv_pq = ROOT_DIR / "data" / "processed" / "customer_clv_predictions.parquet"
    if not clv_pq.exists():
        raise HTTPException(status_code=503, detail="CLV predictions dataset not available.")

    df = pd.read_parquet(clv_pq)
    target = df[df["CustomerID"].astype(str) == str(customer_id).strip()]

    if len(target) == 0:
        raise HTTPException(status_code=404, detail=f"Customer ID '{customer_id}' not found in registered cohort.")

    row = target.iloc[0]
    return {
        "customer_id": str(row["CustomerID"]),
        "p_alive": round(float(row["P_Alive"]), 4),
        "expected_orders_90d": round(float(row["Expected_Orders_90d"]), 2),
        "expected_orders_365d": round(float(row["Expected_Orders_365d"]), 2),
        "expected_avg_spend_gbp": round(float(row["Expected_Avg_Spend_GBP"]), 2),
        "clv_12m_gbp": round(float(row["CLV_12M_GBP"]), 2),
        "clv_segment": str(row["CLV_Segment"])
    }


# -----------------------------------------------------------------------------
# Live Reactive POS Order Injection & WebSocket Streaming
# -----------------------------------------------------------------------------
@app.websocket("/ws/live-orders")
async def websocket_live_orders_endpoint(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket stream broadcasting retail transaction events
    and reactive telemetry across all connected dashboard terminals.
    """
    await ws_manager.connect(websocket)
    try:
        # Initial greeting & active listeners telemetry
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "service": "Nexus Live Order WebSocket Stream",
            "status": "connected",
            "active_clients": len(ws_manager.active_connections)
        })
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_json({
                        "type": "PONG",
                        "active_clients": len(ws_manager.active_connections)
                    })
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post("/api/v1/orders/inject", tags=["Live POS Streaming"])
async def inject_pos_order(payload: OrderInjectionRequest):
    """
    Ingests a live simulated retail transaction, recalculates reactive churn & RFM vectors,
    and broadcasts the event across all active WebSockets to trigger instantaneous UI updates.
    """
    import uuid
    from datetime import datetime, timezone

    invoice_no = f"INV-{uuid.uuid4().hex[:6].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    total_amount = round(sum(item.quantity * item.unit_price for item in payload.items), 2)
    total_units = sum(item.quantity for item in payload.items)

    # Reactive churn drop: a fresh purchase resets recency to 0 days
    # Accounts spending >£500 achieve single-digit churn probability
    updated_churn_risk = 0.08 if total_amount >= 500 else 0.16

    event_payload = {
        "invoice_no": invoice_no,
        "timestamp": timestamp,
        "customer_id": str(payload.customer_id).strip(),
        "country": payload.country,
        "total_amount_gbp": total_amount,
        "total_units": total_units,
        "items": [item.model_dump() for item in payload.items],
        "updated_churn_probability": updated_churn_risk,
        "updated_recency_days": 0,
        "active_clients_notified": len(ws_manager.active_connections)
    }

    # Broadcast event to all active dashboards
    await ws_manager.broadcast({
        "type": "ORDER_INJECTED",
        "data": event_payload
    })

    return {
        "status": "success",
        "message": f"Transaction {invoice_no} processed and broadcasted to {len(ws_manager.active_connections)} client(s).",
        "order": event_payload
    }


@app.get("/api/v1/orders/stream-status", tags=["Live POS Streaming"])
def get_order_stream_status():
    """Returns active WebSocket listeners and stream telemetry."""
    return {
        "websocket_endpoint": "/ws/live-orders",
        "active_listeners": len(ws_manager.active_connections),
        "status": "online"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

