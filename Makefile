.PHONY: help setup ingest clean features train test sql export api web all

help:
	@echo "Available commands:"
	@echo "  make setup      - Install Python dependencies"
	@echo "  make ingest     - Download and extract raw UCI dataset"
	@echo "  make clean      - Run data cleaning pipeline (saves CSV & Parquet)"
	@echo "  make features   - Engineer RFM, Time-Series lags, and Churn features"
	@echo "  make train      - Train and serialize all ML models"
	@echo "  make clv        - Train BG/NBD and Gamma-Gamma Customer Lifetime Value models"
	@echo "  make test       - Run 21-test pytest suite"
	@echo "  make sql        - Execute DuckDB in-memory SQL analytical queries"
	@echo "  make export     - Sync pipeline and model predictions to data/nexus_data.json"
	@echo "  make api        - Start FastAPI ML serving layer on http://localhost:8000"
	@echo "  make web        - Start local web dashboard on http://localhost:8080"
	@echo "  make docker-up  - Run full-stack application with Docker Compose"
	@echo "  make docker-down - Stop all Docker Compose containers"
	@echo "  make all        - Full pipeline: clean -> train -> test -> export"

setup:
	pip install --upgrade pip
	pip install -r requirements.txt

ingest:
	python src/data/ingest.py

clean:
	python src/data/clean.py

features:
	python src/features/rfm.py
	python src/features/sales_features.py
	python src/features/churn_features.py

train:
	python src/models/segmentation.py
	python src/models/sales_forecasting.py
	python src/models/churn_prediction.py
	python src/models/recommender.py
	python src/models/clv_btyd.py

clv:
	python src/models/clv_btyd.py

test:
	pytest tests/ -v

sql:
	python src/data/run_queries.py

export:
	python scripts/export_frontend_data.py

api:
	uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload

web:
	python3 -m http.server 8080

docker-up:
	docker compose up --build

docker-down:
	docker compose down

all: clean train test export

