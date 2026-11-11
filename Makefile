.PHONY: help setup ingest clean features train test sql export api web all drift clv docker-up docker-down lint ci

VENV := ./venv
PYTHON := $(shell if [ -f $(VENV)/bin/python ]; then echo $(VENV)/bin/python; else which python3 || echo python; fi)
PYTEST := $(shell if [ -f $(VENV)/bin/pytest ]; then echo $(VENV)/bin/pytest; else which pytest || echo pytest; fi)

help:
	@echo "Available commands:"
	@echo "  make setup      - Install Python dependencies"
	@echo "  make ingest     - Download and extract raw UCI dataset"
	@echo "  make clean      - Run data cleaning pipeline (saves CSV & Parquet)"
	@echo "  make features   - Engineer RFM, Time-Series lags, and Churn features"
	@echo "  make train      - Train and serialize all ML models"
	@echo "  make clv        - Train BG/NBD and Gamma-Gamma Customer Lifetime Value models"
	@echo "  make drift      - Run statistical data drift radar (KS test & PSI)"
	@echo "  make lint       - Validate Python syntax across src and test suites"
	@echo "  make test       - Run 44-test pytest suite"
	@echo "  make ci         - Execute full local CI check (lint + test + manifest)"
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
	$(PYTHON) src/data/ingest.py

clean:
	$(PYTHON) src/data/clean.py

features:
	$(PYTHON) src/features/rfm.py
	$(PYTHON) src/features/sales_features.py
	$(PYTHON) src/features/churn_features.py

train:
	$(PYTHON) src/models/segmentation.py
	$(PYTHON) src/models/sales_forecasting.py
	$(PYTHON) src/models/churn_prediction.py
	$(PYTHON) src/models/recommender.py
	$(PYTHON) src/models/clv_btyd.py

clv:
	$(PYTHON) src/models/clv_btyd.py

drift:
	$(PYTHON) src/models/drift_monitor.py

lint:
	$(PYTHON) -m compileall -q src/ tests/

test:
	$(PYTEST) tests/ -v

ci: lint test
	@$(PYTHON) -c "import json; m = json.load(open('models/model_manifest.json')); assert len(m['models']) == 5; assert m['governance_status'] in ['CERTIFIED_HEALTHY', 'PASS']; print('Local CI Verification: ALL 5 ENGINES CERTIFIED HEALTHY')"

sql:
	$(PYTHON) src/data/run_queries.py

export:
	$(PYTHON) scripts/export_frontend_data.py

api:
	$(VENV)/bin/uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload

web:
	python3 -m http.server 8080

docker-up:
	docker compose up --build

docker-down:
	docker compose down

all: clean train test export

