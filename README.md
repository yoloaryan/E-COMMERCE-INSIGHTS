# E-Commerce Customer Intelligence & Sales Prediction System

[![Live Demo](https://img.shields.io/badge/Live_Demo-Render_Web_App-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://e-commerce-insights.onrender.com/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/yoloaryan/E-COMMERCE-INSIGHTS)

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.9.1-orange.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-3.2.0-red.svg)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E.svg?logo=javascript&logoColor=black)
![HTML5 / CSS3](https://img.shields.io/badge/Frontend-HTML5_%2F_CSS3-E34F26.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

> [!IMPORTANT]
> 🚀 **Live Production Web Application:** **[https://e-commerce-insights.onrender.com/](https://e-commerce-insights.onrender.com/)**
>
> Built as a responsive, compositor-optimized **Liquid Glass** single-page web application (HTML5 / CSS3 / Vanilla JavaScript) backed by FastAPI & DuckDB microservices (`v4.5.0`, **28 Phases**, **142+ automated tests**). Experience **15 operational intelligence modules**: Executive BI & Boardroom Briefing Exports, Customer Segmentation & Cohort Retention Heatmaps, Demand Forecasting, Churn Early-Warning with **Kaplan-Meier Survival & Exact Shapley XAI**, Item-Item & Apriori Market Basket Rules, **Kimball Star-Schema SQL Workbench + 7-Rule DQ Suite**, Customer-360 Dossier, Inventory EOQ, **Causal T-Learner Uplift & DiD Incrementality**, Dynamic Pricing & A/B Labs, Isolation Forest Fraud Radar, Live POS Simulator & **Indian GST (`CGST/SGST/IGST + HSN`) Tax Invoice Studio**, Autonomous Watchdog, SQLite WAL Persistence, and Multi-Tenant RBAC Security.

An industry-grade Data Science, Machine Learning, and Business Intelligence platform built on **541,909 real-world transnational e-commerce records**. 

This system integrates **Customer Behavioral Segmentation (RFM + K-Means + Cohorts)**, **Macro Demand & Sales Forecasting**, **Churn Early-Warning**, **Collaborative Filtering & Apriori Basket Rules**, **Dynamic Pricing & A/B Labs**, **Inventory EOQ & Supply Optimization**, **Isolation Forest Fraud Detection**, and **Multi-Tenant RBAC Security** into an interactive **Enterprise Web Intelligence Suite**.

---

## 🏛️ System Architecture

```
                                  DATA & ETL PIPELINE
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │         UCI Online Retail Raw Records (541,909 rows, 374 days)              │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                        DUAL-DATASET ARCHITECTURE                            │
  │  Store-Wide Cleaned (536,636 rows)   │  Customer-Centric (396,470 rows)     │
  │  (Guest Checkouts Retained for Macro)│  (4,334 Unique Verified Customers)   │
  └──────────────────┬───────────────────┴──────────────────┬───────────────────┘
                     │                                      │
                     ▼                                      ▼
       SALES DEMAND FORECASTING                CUSTOMER INTELLIGENCE
  ┌──────────────────────────────────────┐  ┌───────────────────────────────────┐
  │ • Autoregressive Lags (Lag 1, 7, 14) │  │ • RFM Feature Engineering         │
  │ • Rolling Averages (7d, 30d)         │  │ • Natural Log1p Scaling           │
  │ • Chronological Split (80/20)        │  │ • K-Means (K=4 via Elbow & Sil)   │
  │ • Random Forest Regressor (MAE: £12k)│  │ • Champions, Loyal, At-Risk       │
  └──────────────────┬───────────────────┘  └───────────────────┬───────────────┘
                     │                                          │
                     ├──────────────────┐                       │
                     ▼                  ▼                       ▼
           CHURN EARLY WARNING   RECOMMENDER ENGINE       SQL ANALYTICS MART
  ┌────────────────────────────┐ ┌───────────────────┐ ┌───────────────────────┐
  │ • Inactivity Cutoff Window │ │ • Item-Item CF    │ │ • Production MySQL    │
  │ • Recall Priority (75.86%) │ │ • Cosine Affinities││ • RFM Aggregations    │
  │ • £191.8k Exposure Flagged │ │ • Cross-Sell Drops│ │ • Churn Window Query  │
  └─────────────┬──────────────┘ └─────────┬─────────┘ └───────────┬───────────┘
                │                          │                       │
                └──────────────────────────┼───────────────────────┘
                                           ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │         NEXUS RETAIL AI WEB APPLICATION (`index.html`, `style.css`, `app.js`)│
  │  🌐 Live at: https://e-commerce-insights.onrender.com/                       │
  │  Executive KPIs • Customer Segmentation • Sales Forecaster • Churn Early   │
  │  Warning • Recommender Mart • POS Simulator • MLOps Console • Audit Stream  │
  └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💼 Business Problem & Quantifiable Impact

In non-contractual e-commerce, businesses face four core existential bottlenecks:

| Business Bottleneck | Industry Reality | ML Solution | Quantified ROI |
| :--- | :--- | :--- | :--- |
| **High Customer Acquisition Cost (CAC)** | Acquiring new customers is $5\times$ to $7\times$ more expensive than retention. | **Customer Churn Classifier (Random Forest)** | Identified **22 At-Risk VIP Accounts** representing **£191,892.72 in revenue exposure**, enabling proactive outreach. |
| **One-Size-Fits-All Marketing** | Blanket promotional blast emails yield $<2\%$ conversion and fatigue users. | **RFM Segmentation + K-Means Clustering** | Uncovered that **$16.3\%$ of customers (Champions)** generate **$64.55\%$ of total gross revenue** (£7,993 avg spend). |
| **Stockouts & Overstock Working Capital** | Inaccurate demand forecasting leads to tied-up capital or lost high-margin sales. | **Time-Series Sales Forecasting (Ensemble ML)** | **Random Forest** achieved **26.28% MAPE** on peak Q4 sales spikes, reducing safety stock requirements by an estimated $18\%$. |
| **Low Basket Size / Cart Abandonment** | Consumers struggle to discover complementary products across thousands of SKUs. | **Item-Based Collaborative Filtering** | Delivers sub-millisecond, highly coherent cross-sell items (e.g. Regency Teacups for Regency Cakestand). |

---

## 📊 Summary of Model Evaluation Results

### 1. Customer Segmentation (Module 2)
- **Optimal Cluster Count ($K=4$)**: Justified through Inertia Elbow inflection and Silhouette Score ($0.3375$).

| Segment Name | Customer Count | Avg Recency | Avg Orders | Avg Spend | % of Customers | % of Gross Revenue |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Champions (VIPs)** | 708 | 11.9 days | 13.7 | £7,993.48 | 16.3% | **64.55%** |
| **At-Risk / Lapsing** | 1,180 | 69.1 days | 4.1 | £1,784.53 | 27.2% | **24.02%** |
| **Loyal Customers** | 844 | 19.0 days | 2.1 | £530.01 | 19.5% | **5.10%** |
| **Occasional / Hibernating**| 1,602 | 184.7 days | 1.3 | £346.63 | 37.0% | **6.33%** |

---

### 2. Time-Series Sales Forecasting (Module 3)
- **Validation**: Strict chronological split (first 80% training, unseen final 20% test set).

| Model | MAE (£) | RMSE (£) | MAPE (%) | $R^2$ Score | Selection Verdict |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Random Forest Regressor** | **£12,464.66** | **£22,989.70** | **$26.28\%$** | **$0.4281$** | **Production Winner** |
| **XGBoost Regressor** | £14,826.75 | £24,854.73 | $29.13\%$ | $0.3315$ | High-performing alternative |
| **Linear Regression (Baseline)** | £19,180.12 | £28,919.85 | $37.39\%$ | $0.0949$ | Underfitted |

*Top Predictors*: `DayOfWeek` (28.06%), `Lag_7` (22.06%), `RollingMean_30` (7.37%).

---

### 3. Customer Churn Classification (Module 4)
- **Target Definition**: 0 orders placed in the 90-day future observation window.

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Random Forest Classifier** | **$0.6528$** | **$0.5729$** | **$0.7586$** | **$0.6528$** | **$0.7163$** | **Production Winner** |
| **XGBoost Classifier** | $0.6365$ | $0.5613$ | $0.7103$ | $0.6271$ | $0.7122$ | Highly competitive |
| **Logistic Regression** | $0.6439$ | $0.5658$ | $0.7414$ | $0.6418$ | $0.7105$ | Solid linear baseline |

*Top Predictors*: `HistoricalFrequency` (24.46%), `HistoricalMonetary` (17.92%), `HistoricalUnits` (12.93%).

---

### 4. Product Recommendations (Module 5)
- **Methodology**: Sparse Item-Item Cosine Similarity on binary implicit feedback interaction matrices.
- **Sample Cross-Sell Output for `[22423] Regency Cakestand 3 Tier`**:
  1. `[22699] Roses Regency Teacup And Saucer` (£2.95) — Cosine Similarity: `0.5258`
  2. `[22697] Green Regency Teacup And Saucer` (£2.95) — Cosine Similarity: `0.5086`
  3. `[22698] Pink Regency Teacup And Saucer` (£2.95) — Cosine Similarity: `0.4886`
  4. `[23245] Set Of 3 Regency Cake Tins` (£4.95) — Cosine Similarity: `0.4668`
  5. `[23173] Regency Teapot Roses` (£9.95) — Cosine Similarity: `0.4535`

---

## 📂 Project Repository Structure

```
├── README.md                          # Executive project documentation
├── requirements.txt                   # Locked production dependencies
├── .gitignore                         # Ignores large raw datasets, models, venv
├── data/
│   ├── raw/                           # Raw Excel & zip archives
│   └── processed/                     # Cleaned store, customer, and feature tables
│       ├── online_retail_cleaned.csv
│       ├── online_retail_customer_centric.csv
│       ├── customer_segments.csv
│       ├── daily_sales_features.csv
│       ├── sales_forecast_results.csv
│       ├── customer_churn_features.csv
│       └── customer_churn_predictions.csv
├── notebooks/                         # Self-contained exploratory & modeling notebooks
│   ├── 01_data_cleaning_eda.ipynb
│   ├── 02_customer_segmentation.ipynb
│   ├── 03_sales_prediction.ipynb
│   ├── 04_churn_prediction.ipynb
│   └── 05_product_recommendation.ipynb
├── src/                               # Modular Python packages
│   ├── data/                          # Ingestion, cleaning, EDA, upload importer & Kimball warehouse
│   │   ├── ingest.py
│   │   ├── clean.py
│   │   ├── eda.py
│   │   ├── importer.py
│   │   ├── run_queries.py
│   │   └── warehouse.py               # DuckDB Star Schema (4 Dim, 2 Fact) + 7 SQL DQ checks
│   ├── features/                      # Feature stores (RFM, Time-Series lags, Churn)
│   │   ├── rfm.py
│   │   ├── sales_features.py
│   │   └── churn_features.py
│   ├── models/                        # Predictive, Causal, Survival, Supply & Finance ML engines
│   │   ├── segmentation.py
│   │   ├── sales_forecasting.py
│   │   ├── churn_prediction.py
│   │   ├── clv_btyd.py                # BG/NBD + Gamma-Gamma Probabilistic CLV
│   │   ├── recommender.py
│   │   ├── basket_rules.py            # Apriori Association Rules & Bundle Evaluator
│   │   ├── cohort_analytics.py        # Cohort Retention & Markov Migration Engine
│   │   ├── customer_360.py            # Unified Customer-360 Financial & Action Dossier
│   │   ├── pricing_elasticity.py      # Elasticity & Frequentist A/B Power/Test Engine
│   │   ├── inventory_optimization.py  # ABC/XYZ Classification & EOQ / Safety Stock
│   │   ├── financial_waterfall.py     # Return & Refund P&L Margin Waterfall
│   │   ├── anomaly_detection.py       # Isolation Forest Fraud & Quarantine Scoring
│   │   ├── causal_uplift.py           # Dual-Model T-Learner CATE, Qini & DiD Attribution
│   │   ├── survival_xai.py            # Kaplan-Meier, Weibull Hazard & Exact Shapley XAI
│   │   └── drift_monitor.py           # PSI / KS-Test Data Drift & MLOps Retrain
│   ├── api/                           # FastAPI Microservices, Security, Watchdog, Invoices
│   │   ├── server.py
│   │   ├── security.py                # PBKDF2, JWT, Multi-Tenant RBAC & Audit Stream
│   │   ├── copilot.py                 # DuckDB Text-to-SQL AI Copilot
│   │   ├── campaigns.py               # Retention Dispatch & Voucher Engine
│   │   ├── integrations.py            # Shopify / Stripe / WooCommerce Signed Webhooks
│   │   ├── watchdog.py                # Autonomous 4-Engine Telemetry Watchdog
│   │   ├── briefing.py                # 6-Engine Executive Boardroom Pack Generator
│   │   └── invoices.py                # Indian GST (CGST/SGST/IGST + HSN) & VAT Engine
│   └── utils/
│       └── state_store.py             # Persistent SQLite WAL State Store
├── models/                            # Serialized model binaries (.joblib)
│   ├── kmeans_rfm_model.joblib
│   ├── rfm_scaler.joblib
│   ├── best_sales_forecaster.joblib
│   ├── best_churn_classifier.joblib
│   ├── churn_scaler.joblib
│   ├── item_similarity_matrix.joblib
│   └── product_catalog.joblib
├── tests/                             # 142+ Pytest Unit, Integration & UI Integrity Checks
├── sql/
│   └── schema_and_queries.sql         # Production MySQL table schema & analytical queries
└── app/
    └── main.py                        # Interactive Streamlit BI Command Center
```

---

## 🚀 Quickstart & Installation

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/your-username/ecommerce-intelligence-ml.git
cd ecommerce-intelligence-ml

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Run the Full Automated Pipeline
To execute data ingestion, cleaning, feature engineering, and model training in order:
```bash
# Ingest & Clean
python src/data/ingest.py
python src/data/clean.py

# Customer Segmentation (RFM + K-Means)
python src/models/segmentation.py

# Sales Forecasting (Time-Series ML)
python src/models/sales_forecasting.py

# Churn Prediction (Classification)
python src/models/churn_prediction.py

# Product Recommendation Engine (Collaborative Filtering)
python src/models/recommender.py

# In-Process SQL Analytics Mart (DuckDB)
python src/data/run_queries.py

# Execute Production Test Suite
pytest tests/ -v
```

### 3. Launch or Access the Web Application

#### A. Live Production Cloud Deployment (Render)
Directly test and explore the live hosted application:
👉 **[https://e-commerce-insights.onrender.com/](https://e-commerce-insights.onrender.com/)**

#### B. Standalone Local Web Application (HTML5 / CSS3 / Vanilla JS)
```bash
python3 -m http.server 8080
```
Open your browser at `http://localhost:8080`.

#### C. Optional Python ML Diagnostic Console
```bash
streamlit run app/main.py
```
Open your browser at `http://localhost:8501`.

#### D. Production FastAPI ML Serving Layer
```bash
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger OpenAPI documentation available at `http://localhost:8000/docs`.
- **Core ML & Forecasting**: `POST /api/v1/forecast/sales`, `POST /api/v1/churn/predict`, `POST /api/v1/segment/rfm`, `GET /api/v1/clv/summary`, `GET /api/v1/recommend/item/{stock_code}`, `GET /api/v1/analytics/kpis`.
- **Kimball Warehouse & Customer-360**: `GET /api/v1/warehouse/schema`, `GET /api/v1/warehouse/data-quality`, `POST /api/v1/warehouse/query`, `GET /api/v1/customers/{customer_id}/360`.
- **Causal ML & Survival XAI**: `GET /api/v1/causal/uplift-report`, `POST /api/v1/causal/did-attribution`, `GET /api/v1/survival/kaplan-meier-report`, `GET /api/v1/survival/explain/{customer_id}`, `POST /api/v1/survival/simulate-intervention`.
- **Indian GST Tax Invoicing & Finance**: `GET /api/v1/invoices/recent`, `GET /api/v1/invoices/{invoice_no}`, `POST /api/v1/invoices/generate`, `GET /api/v1/invoices/{invoice_no}/html`, `GET /api/v1/finance/waterfall-report`.
- **Operations, Security & Telemetry**: `POST /api/v1/pricing/ab-test/run`, `GET /api/v1/inventory/optimization`, `POST /api/v1/fraud/score-transaction`, `GET /api/v1/watchdog/status`, `GET /api/v1/auth/rbac-matrix`.

Execute full CI & UI integrity checks anytime:
```bash
make ci
```

#### E. One-Click Full-Stack Docker Compose
```bash
docker compose up --build
```
Spins up both the Python FastAPI backend (`http://localhost:8000`) and Nginx Web Dashboard (`http://localhost:8080`) with automated reverse proxy routing and container health checks.

---

## 🌐 Cloud Deployment Guide (Render & Vercel)

### 1. Live Deployment on Render (HTML / CSS / JavaScript)
The live application is hosted at: **[https://e-commerce-insights.onrender.com/](https://e-commerce-insights.onrender.com/)**

This repository is configured specifically for Render Static Sites in [`render.yaml`](render.yaml) and [`Procfile`](Procfile):
1. Push your repository to GitHub: `https://github.com/yoloaryan/E-COMMERCE-INSIGHTS`.
2. Go to the [Render Dashboard](https://dashboard.render.com) and click **"New +"** ➔ **"Static Site"** (or **"Blueprint"**).
3. Connect your GitHub repository: `yoloaryan/E-COMMERCE-INSIGHTS`.
4. Configure:
   - **Name**: `e-commerce-insights`
   - **Build Command**: `echo 'Static assets ready'` (or leave blank)
   - **Publish Directory**: `.`
5. Click **Create Static Site**. Render deploys the platform with automatic HTTPS, zero cold starts, and global CDN acceleration.

### 2. Deploying to Vercel (Edge CDN)
This repository includes a preconfigured [`vercel.json`](vercel.json):
1. Go to [Vercel](https://vercel.com) and click **"Add New Project"**.
2. Import your `yoloaryan/E-COMMERCE-INSIGHTS` repository.
3. Keep default settings (Framework Preset: **Other**, Root Directory: `./`).
4. Click **Deploy**. Vercel will instantly serve the dashboard on an edge CDN URL.

---

## 💡 Placement Interview Defense Guide

When discussing this project in a Technical or Behavioral interview, highlight these key design decisions:

1. **Why not drop missing `CustomerID` immediately?**
   > *"Dropping missing customer IDs upfront is a common novice error. Guest checkouts represented nearly 25% of all purchases and over £1.5M in sales. Dropping them would severely bias store-level demand forecasts. I implemented a Dual-Dataset Architecture: store-wide for macro sales forecasting, and customer-centric for RFM, churn, and recommendations."*

2. **Why log-transform features before K-Means clustering?**
   > *"K-Means uses Euclidean distance. Because e-commerce spend exhibits extreme power-law skewness ($>20$), unscaled whale customers would dominate the distance metric, collapsing 98% of users into a single cluster. Applying $x' = \ln(1 + x)$ followed by Z-Score standardization equilibrates geometric weights."*

3. **How did you prevent data leakage in time-series sales forecasting?**
   > *"I strictly avoided random $K$-fold splits. All lag and rolling window features were shifted by at least one period, and the dataset was divided chronologically: the first 80% for training and the final unseen 20% for testing during the peak Q4 holiday surge."*

4. **Why prioritize Recall over Precision in Churn Prediction?**
   > *"In customer retention, a False Negative (missing an at-risk customer) means permanent loss of future Customer Lifetime Value. A False Positive simply results in sending an extra appreciation or discount email. Our model achieved 75.86% Recall, catching over three-quarters of all departing accounts."*

---

## 📜 License
Distributed under the MIT License. Developed for enterprise Data Science & Machine Learning portfolio demonstrations.
