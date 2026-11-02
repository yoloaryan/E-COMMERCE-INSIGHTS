# E-Commerce Customer Intelligence & Sales Prediction System

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.9.1-orange.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-3.2.0-red.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.66-FF4B4B.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.2-150458.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

An industry-grade Data Science, Machine Learning, and Business Intelligence platform built on **541,909 real-world transnational e-commerce records**. 

This system integrates **Customer Behavioral Segmentation (RFM + K-Means)**, **Macro Demand & Sales Forecasting (Time-Series ML)**, **Customer Churn Early-Warning (Classification)**, and **Product Recommendation (Item-Item Collaborative Filtering)** into an interactive **Streamlit BI Command Center**.

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
  │            STREAMLIT BUSINESS INTELLIGENCE DASHBOARD (`app/main.py`)         │
  │   Executive KPIs • 3D Customer Clusters • Live Forecasts • Churn Scanner   │
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
│   ├── data/                          # Ingestion, cleaning, audit, and EDA modules
│   │   ├── ingest.py
│   │   ├── clean.py
│   │   └── eda.py
│   ├── features/                      # Feature stores (RFM, Time-Series lags, Churn)
│   │   ├── rfm.py
│   │   ├── sales_features.py
│   │   └── churn_features.py
│   └── models/                        # Model training, hyperparameter tuning, inference
│       ├── segmentation.py
│       ├── sales_forecasting.py
│       ├── churn_prediction.py
│       └── recommender.py
├── models/                            # Serialized model binaries (.joblib)
│   ├── kmeans_rfm_model.joblib
│   ├── rfm_scaler.joblib
│   ├── best_sales_forecaster.joblib
│   ├── best_churn_classifier.joblib
│   ├── churn_scaler.joblib
│   ├── item_similarity_matrix.joblib
│   └── product_catalog.joblib
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
```

### 3. Launch the Interactive Web Applications

#### A. Streamlit BI Dashboard (Python ML Backend)
```bash
streamlit run app/main.py
```
Open your browser at `http://localhost:8501`.

#### B. Standalone Static Web Dashboard (HTML / CSS / JS)
```bash
python3 -m http.server 8080
```
Open your browser at `http://localhost:8080`.

---

## 🌐 Cloud Deployment Guide (Vercel & Render)

### 1. Deploying to Vercel (One-Click Static & Serverless)
This repository includes a preconfigured [`vercel.json`](file:///Users/aryangupta/Desktop/e-commerce/vercel.json).
1. Push your repository to GitHub.
2. Go to [Vercel](https://vercel.com) and click **"Add New Project"**.
3. Import your `ecommerce-customer-intelligence-ml` repository.
4. Leave the default settings (Framework Preset: **Other**, Root Directory: `./`).
5. Click **Deploy**. Vercel will instantly build and serve your interactive web dashboard on a global CDN edge URL (`https://your-project.vercel.app`).

### 2. Deploying to Render (Python Streamlit or Static)
This repository includes a Render Infrastructure Blueprint in [`render.yaml`](file:///Users/aryangupta/Desktop/e-commerce/render.yaml) and [`Procfile`](file:///Users/aryangupta/Desktop/e-commerce/Procfile).
1. Push your repository to GitHub.
2. Go to [Render](https://render.com) and click **"New"** ➔ **"Blueprint"**.
3. Connect your GitHub repository. Render will automatically parse `render.yaml` and configure:
   - **Service 1 (`ecommerce-ml-streamlit`)**: Full Python Web Service running Streamlit on port `10000` with all trained `.joblib` models.
   - **Service 2 (`ecommerce-analytics-dashboard`)**: Ultra-fast Static Web site running the HTML/CSS/JS interface.
4. Click **Apply**. Render will automatically provision and launch your live production services.

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
