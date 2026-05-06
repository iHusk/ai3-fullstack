# Northbrook Q&A — Streamlit Deployment
# Session 4.1: Deployment Readiness
#
# Build:  docker build -t northbrook-qa .
# Run:    docker run -p 8501:8501 --env-file .env northbrook-qa

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install system dependencies for ChromaDB
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and config
COPY app/ app/
COPY pipeline/ pipeline/
COPY data/ data/
COPY scripts/ scripts/
COPY .streamlit/ .streamlit/
COPY student_config.yaml .

# ChromaDB (pre-populated vector store, ~13MB).
# Required so the deployed app has the same retrieval corpus as local dev —
# Community Cloud's filesystem is ephemeral, so we ship the data IN the image.
COPY chroma_db/ chroma_db/

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app/main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
