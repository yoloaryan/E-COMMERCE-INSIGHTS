# Production Dockerfile for E-Commerce Customer Intelligence & ML Platform
FROM python:3.11-slim

# System dependencies for scientific packages and OpenMP
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy repository assets
COPY . .

# Expose default Streamlit port
EXPOSE 8501

ENV PYTHONUNBUFFERED=1

CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
