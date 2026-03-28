# ── Stage 1: Build the React frontend ──
FROM node:18-slim AS frontend-build

WORKDIR /frontend

# Copy package files and install deps
COPY frontend/package.json frontend/yarn.lock* ./
RUN yarn install --frozen-lockfile --network-timeout 120000 2>/dev/null || yarn install --network-timeout 120000

# Copy source and build
COPY frontend/ ./

# Empty string → frontend makes relative API calls to same origin
ENV REACT_APP_BACKEND_URL=""
RUN yarn build


# ── Stage 2: Python backend + built frontend ──
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY backend/requirements.docker.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend from stage 1
COPY --from=frontend-build /frontend/build ./static

# Default env vars (override at runtime)
ENV CHATWOOT_URL=""
ENV CHATWOOT_API_TOKEN=""
ENV CHATWOOT_ACCOUNT_ID=""
ENV MONGO_URL="mongodb://mongodb:27017"
ENV DB_NAME="chatwoot_mcp"
ENV CORS_ORIGINS="*"

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/')" || exit 1

# Run FastAPI serving both API + frontend
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
