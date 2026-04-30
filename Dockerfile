# python:3.10-slim chosen over alpine to avoid binary wheel issues
# with pandas, httpx, and other compiled dependencies.
FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY tiktok_ads_mcp/ ./tiktok_ads_mcp/
COPY oauth/ ./oauth/
COPY server_http.py .

# Cloud Run injects PORT automatically; default 8080 for local testing
ENV PORT=8080

# Run the HTTP server (not the stdio server.py)
CMD ["python", "server_http.py"]
