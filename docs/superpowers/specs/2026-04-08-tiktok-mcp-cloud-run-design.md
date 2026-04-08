# TikTok Ads MCP — Google Cloud Run Deployment Design

**Date:** 2026-04-08
**Status:** Approved
**Target endpoint:** `https://tiktok-mcp-825147945372.asia-southeast1.run.app/mcp`

---

## Context

The TikTok Ads MCP server currently runs stdio-only, suitable for local Claude Desktop use. This design adds a streamable HTTP transport so the server can be deployed on Google Cloud Run and shared across a team, matching the pattern established by the LinkedIn Ads MCP (`server-sse.ts` → Starlette/uvicorn equivalent in Python).

Existing MCPs in the same GCP project for reference:
- Google Analytics: `ga-mcp-825147945372.asia-southeast1.run.app/mcp`
- Google Ads: `ads-mcp-825147945372.asia-southeast1.run.app/mcp`
- Meta Ads: `fb-ads-mcp-825147945372.asia-southeast1.run.app/sse`
- LinkedIn Ads: `li-ads-mcp-825147945372.asia-southeast1.run.app/mcp`

---

## Architecture

```
Claude AI / Team members
        │
        │ HTTPS POST /mcp
        ▼
Google Cloud Run (asia-southeast1)
  tiktok-mcp-825147945372
        │
        ▼
  server_http.py  (Starlette + uvicorn)
  ┌─────────────────────────────────┐
  │  GET  /health  → JSON status    │
  │  ALL  /mcp     → auth check     │
  │                → StreamableHTTP │
  │                → MCP server     │
  │                → TikTok tools   │
  └─────────────────────────────────┘
        │
        ▼
  TikTok Business API
  business-api.tiktok.com
```

**Transport:** MCP Streamable HTTP (`StreamableHTTPServerTransport`), stateless — one transport instance per request, server closed after response. Matches LinkedIn Ads MCP pattern exactly.

**`server.py` is not modified.** Stdio transport continues to work for local Claude Desktop use.

---

## Components

### 1. `server_http.py` (new)

Starlette ASGI application. Python equivalent of LinkedIn's `server-sse.ts`.

**Routes:**
- `GET /health` — returns `{"status": "healthy", "service": "tiktok-ads-mcp", "version": "0.1.3", "transport": "streamable-http"}`. No auth required. Used by Cloud Run health checks.
- `POST /mcp` (and other methods) — runs auth middleware, then creates a `StreamableHTTPServerTransport` + MCP server per request. Server closed on response finish/close/error.

**Auth middleware:**
- Reads `MCP_API_KEY` from env at startup.
- If not set: no auth enforced (open access).
- If set: requires `Authorization: Bearer <key>` header on `/mcp` requests. Returns `401` if missing/malformed, `403` if key mismatch. `/health` is always exempt.

**CORS:** Permissive (`*`) to allow claude.ai connectors. Headers: `Content-Type`, `Authorization`, `Mcp-Session-Id`. Exposed: `Mcp-Session-Id`.

**MCP server factory:** A `create_mcp_server()` function registers all six tools against a fresh `Server` instance each request. Tools delegate to the existing tool functions (`get_business_centers`, `get_campaigns`, etc.) via `TikTokAdsClient`. Credential validation happens inside `TikTokAdsClient.__init__()` on each request, so missing env vars return a clean error rather than crashing the container.

**Startup:** `uvicorn.run(starlette_app, host="0.0.0.0", port=PORT)` where `PORT = int(os.getenv("PORT", "8080"))`.

### 2. `Dockerfile` (new)

```
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
CMD ["python", "server_http.py"]
```

- Uses `python:3.10-slim` (not alpine — avoids binary wheel issues with pandas/httpx).
- Does not copy `.env` files (secrets injected by Cloud Run at runtime).
- No `EXPOSE` directive needed (Cloud Run ignores it; PORT env var controls the port).

### 3. `cloudbuild.yaml` (new)

Three steps: build image → push to Artifact Registry → deploy to Cloud Run.

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'REGION-docker.pkg.dev/PROJECT/REPO/tiktok-ads-mcp:$COMMIT_SHA', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'REGION-docker.pkg.dev/PROJECT/REPO/tiktok-ads-mcp:$COMMIT_SHA']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'gcloud'
      - 'run'
      - 'deploy'
      - 'tiktok-ads-mcp'
      - '--image=REGION-docker.pkg.dev/PROJECT/REPO/tiktok-ads-mcp:$COMMIT_SHA'
      - '--region=asia-southeast1'
      - '--platform=managed'
      - '--allow-unauthenticated'
```

Placeholders (`REGION`, `PROJECT`, `REPO`) are filled in at deploy time or via substitution variables.

A companion `deploy.sh` script provides the manual one-shot `gcloud run deploy` command with all flags pre-filled, so the team can deploy without Cloud Build if needed.

### 4. `requirements.txt` (updated)

Add `uvicorn>=0.30.0`. Starlette is already a transitive dependency of `mcp>=1.9.0` so no explicit pin needed (but can be added for reproducibility).

### 5. `pyproject.toml` (fix)

Change `requires-python = ">=3.14.0"` → `">=3.10"` to match the chosen runtime.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TIKTOK_APP_ID` | Yes | TikTok Marketing API app ID |
| `TIKTOK_SECRET` | Yes | TikTok Marketing API secret |
| `TIKTOK_ACCESS_TOKEN` | Yes | Long-lived access token |
| `TIKTOK_ADVERTISER_ID` | No | Default advertiser (optional) |
| `TIKTOK_SANDBOX` | No | Set `true` for sandbox API |
| `MCP_API_KEY` | No | Bearer token for team auth. If unset, no auth enforced. |
| `PORT` | No | HTTP port (default: `8080`, set automatically by Cloud Run) |

Set via `gcloud run deploy --set-env-vars` or Cloud Run console. Never baked into the image.

---

## Error Handling

- Missing TikTok credentials: `TikTokAdsClient.__init__` raises immediately; MCP tool returns an error JSON response. Container stays healthy (no crash).
- Invalid `MCP_API_KEY`: middleware returns HTTP 401/403 before MCP layer is reached.
- TikTok API errors: existing retry logic in `client.py` (tenacity, 3 attempts) handles transient failures.

---

## Files Changed / Created

| File | Action |
|---|---|
| `server_http.py` | Create |
| `Dockerfile` | Create |
| `cloudbuild.yaml` | Create |
| `deploy.sh` | Create |
| `requirements.txt` | Update (add uvicorn) |
| `pyproject.toml` | Fix requires-python |
| `README.md` | Update with Cloud Run deployment section |
| `server.py` | No change |
| `tiktok_ads_mcp/` | No change |

---

## Out of Scope

- OAuth flow / token refresh (access token is long-lived, managed externally)
- Rate limiting middleware (handled by TikTok API + tenacity retry)
- Persistent session state (stateless by design, matching LinkedIn pattern)
- CI trigger setup (cloudbuild.yaml is provided; connecting to GitHub trigger is a manual GCP console step)
