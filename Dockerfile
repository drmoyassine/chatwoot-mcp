FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Default env vars (override at runtime)
ENV CHATWOOT_URL=""
ENV CHATWOOT_API_TOKEN=""
ENV CHATWOOT_ACCOUNT_ID=""
ENV MONGO_URL="mongodb://mongodb:27017"
ENV DB_NAME="chatwoot_mcp"
ENV CORS_ORIGINS="*"
ENV HOST="0.0.0.0"
ENV PORT="8001"

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/')" || exit 1

# Default: run SSE transport via FastAPI (web-accessible)
# Override with: docker run ... python mcp_stdio.py  (for stdio transport)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
