# Cloud Run Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add streamable-HTTP transport and Google Cloud Run deployment files so the TikTok Ads MCP server can be shared across a team at `https://tiktok-mcp-YOUR_PROJECT_NUMBER.asia-southeast1.run.app/mcp`.

**Architecture:** A new `server_http.py` at the project root wraps the existing FastMCP `app` instance (from `tiktok_ads_mcp/server.py`) with a pure-ASGI auth middleware and CORS layer, then serves it via uvicorn. `server.py` (stdio) is untouched. Mirrors the pattern of `linkedin-ads-mcp/src/server-sse.ts`.

**Tech Stack:** Python 3.10, `mcp>=1.9.0` (FastMCP + StreamableHTTP), `starlette`, `uvicorn`, Docker, Google Cloud Run (asia-southeast1), Cloud Build.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Fix `requires-python` to `>=3.10` |
| `requirements.txt` | Modify | Add `uvicorn>=0.30.0` |
| `server_http.py` | Create | HTTP entry point: health route, auth middleware, CORS, uvicorn runner |
| `tests/__init__.py` | Create | Makes tests/ a package |
| `tests/test_server_http.py` | Create | Tests for auth middleware and health endpoint |
| `Dockerfile` | Create | Container image for Cloud Run |
| `cloudbuild.yaml` | Create | CI/CD pipeline: build → push → deploy |
| `deploy.sh` | Create | Manual one-shot deploy script |
| `README.md` | Modify | Add Cloud Run deployment section |

---

## Task 1: Fix Python version and add uvicorn

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Update `pyproject.toml` requires-python**

  Open `pyproject.toml` and change line 14:
  ```toml
  requires-python = ">=3.10"
  ```

- [ ] **Step 2: Add uvicorn to `requirements.txt`**

  Append to `requirements.txt`:
  ```
  uvicorn>=0.30.0
  ```

  Full file should now read:
  ```
  # Core dependencies for TikTok Ads MCP Server
  requests>=2.32.3
  python-dotenv>=1.0.0

  # MCP (Model Context Protocol) server
  mcp>=1.9.0

  # Data handling (lightweight)
  pandas>=2.2.0

  # HTTP server for Cloud Run deployment
  uvicorn>=0.30.0
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add pyproject.toml requirements.txt
  git commit -m "chore: fix python version to 3.10 and add uvicorn dependency"
  ```

---

## Task 2: Write tests and implement `server_http.py`

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_server_http.py`
- Create: `server_http.py`

### Step 2a — Write the failing tests

- [ ] **Step 1: Create `tests/__init__.py`**

  ```bash
  touch tests/__init__.py
  ```

- [ ] **Step 2: Write `tests/test_server_http.py`**

  Create the file with this content:

  ```python
  """Tests for server_http.py — auth middleware and health endpoint."""

  import json
  import os
  from unittest.mock import patch

  import pytest
  from starlette.applications import Starlette
  from starlette.responses import PlainTextResponse
  from starlette.routing import Route
  from starlette.testclient import TestClient


  # ---------------------------------------------------------------------------
  # Helpers
  # ---------------------------------------------------------------------------

  def _mock_inner(path: str = "/mcp"):
      """Return a minimal Starlette app with one POST route at `path`."""
      async def handler(request):
          return PlainTextResponse("ok")

      return Starlette(routes=[Route(path, handler, methods=["GET", "POST", "DELETE"])])


  def _make_middleware(api_key: str | None, inner=None):
      """Instantiate ApiKeyMiddleware with the given MCP_API_KEY env value."""
      from server_http import ApiKeyMiddleware

      inner = inner or _mock_inner()
      env = {"MCP_API_KEY": api_key} if api_key else {}
      # Patch only during __init__ so self.api_key is set correctly
      with patch.dict(os.environ, env, clear=False):
          if not api_key:
              os.environ.pop("MCP_API_KEY", None)
          return ApiKeyMiddleware(inner)


  # ---------------------------------------------------------------------------
  # ApiKeyMiddleware — no key configured
  # ---------------------------------------------------------------------------

  def test_no_api_key_mcp_request_passes():
      """When MCP_API_KEY is not set, /mcp requests pass through."""
      with patch.dict(os.environ, {}, clear=False):
          os.environ.pop("MCP_API_KEY", None)
          from server_http import ApiKeyMiddleware
          middleware = ApiKeyMiddleware(_mock_inner())

      client = TestClient(middleware, raise_server_exceptions=True)
      resp = client.post("/mcp")
      assert resp.status_code == 200
      assert resp.text == "ok"


  # ---------------------------------------------------------------------------
  # ApiKeyMiddleware — key configured
  # ---------------------------------------------------------------------------

  def test_correct_bearer_token_passes():
      """Correct Bearer token allows /mcp access."""
      middleware = _make_middleware("supersecret")
      client = TestClient(middleware, raise_server_exceptions=True)
      resp = client.post("/mcp", headers={"Authorization": "Bearer supersecret"})
      assert resp.status_code == 200


  def test_wrong_bearer_token_returns_401():
      """Wrong token returns 401 with error message."""
      middleware = _make_middleware("supersecret")
      client = TestClient(middleware, raise_server_exceptions=True)
      resp = client.post("/mcp", headers={"Authorization": "Bearer wrongtoken"})
      assert resp.status_code == 401
      assert "Unauthorized" in resp.json()["error"]


  def test_missing_authorization_header_returns_401():
      """Missing Authorization header returns 401 when key is configured."""
      middleware = _make_middleware("supersecret")
      client = TestClient(middleware, raise_server_exceptions=True)
      resp = client.post("/mcp")
      assert resp.status_code == 401


  def test_malformed_authorization_header_returns_401():
      """Authorization header without 'Bearer ' prefix returns 401."""
      middleware = _make_middleware("supersecret")
      client = TestClient(middleware, raise_server_exceptions=True)
      resp = client.post("/mcp", headers={"Authorization": "supersecret"})
      assert resp.status_code == 401


  # ---------------------------------------------------------------------------
  # ApiKeyMiddleware — /health is always exempt
  # ---------------------------------------------------------------------------

  def test_health_exempt_from_auth():
      """/health never requires auth, even when MCP_API_KEY is set."""
      inner = Starlette(routes=[
          Route("/health", lambda req: PlainTextResponse("healthy"), methods=["GET"]),
      ])
      middleware = _make_middleware("supersecret", inner=inner)
      client = TestClient(middleware, raise_server_exceptions=True)
      resp = client.get("/health")
      assert resp.status_code == 200


  # ---------------------------------------------------------------------------
  # Health endpoint response shape
  # ---------------------------------------------------------------------------

  def test_health_returns_correct_shape():
      """health() returns the expected JSON fields."""
      import asyncio
      from unittest.mock import MagicMock
      from starlette.requests import Request

      # Import health after server_http is importable
      from server_http import health

      mock_request = MagicMock(spec=Request)

      with patch.dict(os.environ, {"MCP_API_KEY": "key123"}):
          response = asyncio.get_event_loop().run_until_complete(health(mock_request))

      body = json.loads(response.body)
      assert body["status"] == "healthy"
      assert body["service"] == "tiktok-ads-mcp"
      assert body["transport"] == "streamable-http"
      assert body["auth"] == "enabled"


  def test_health_auth_disabled_when_no_key():
      """health() reports auth disabled when MCP_API_KEY is not set."""
      import asyncio
      from unittest.mock import MagicMock
      from starlette.requests import Request
      from server_http import health

      mock_request = MagicMock(spec=Request)

      with patch.dict(os.environ, {}, clear=False):
          os.environ.pop("MCP_API_KEY", None)
          response = asyncio.get_event_loop().run_until_complete(health(mock_request))

      body = json.loads(response.body)
      assert body["auth"] == "disabled"
  ```

- [ ] **Step 3: Run tests — verify they all fail with ImportError**

  ```bash
  cd /Users/dhawal/src/tiktok-ads-mcp
  python -m pytest tests/test_server_http.py -v 2>&1 | head -20
  ```

  Expected: `ModuleNotFoundError: No module named 'server_http'`

### Step 2b — Implement `server_http.py`

- [ ] **Step 4: Create `server_http.py`**

  ```python
  #!/usr/bin/env python3
  """TikTok Ads MCP Server — Streamable HTTP transport for Google Cloud Run.

  Entry point for deployed / team use. The stdio transport
  (tiktok_ads_mcp/server.py) is unchanged and continues to work for
  local Claude Desktop installations.

  Pattern mirrors linkedin-ads-mcp/src/server-sse.ts:
  - Stateless: each /mcp request gets its own server instance
  - Optional Bearer token auth via MCP_API_KEY env var
  - Public /health endpoint for Cloud Run health checks
  - Permissive CORS for claude.ai connectors
  """

  import logging
  import os

  import uvicorn
  from starlette.middleware.cors import CORSMiddleware
  from starlette.requests import Request
  from starlette.responses import JSONResponse

  from tiktok_ads_mcp.server import app  # FastMCP instance

  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)

  PORT = int(os.getenv("PORT", "8080"))


  # ---------------------------------------------------------------------------
  # Health check
  # Registered on the FastMCP app so it is included in the Starlette routes
  # returned by app.streamable_http_app(). Always public — no auth required.
  # ---------------------------------------------------------------------------

  @app.custom_route("/health", methods=["GET"])
  async def health(request: Request) -> JSONResponse:
      """Public health check used by Cloud Run uptime monitoring."""
      return JSONResponse({
          "status": "healthy",
          "service": "tiktok-ads-mcp",
          "version": "0.1.3",
          "transport": "streamable-http",
          "auth": "enabled" if os.getenv("MCP_API_KEY") else "disabled",
      })


  # ---------------------------------------------------------------------------
  # Auth middleware
  # Pure ASGI middleware (not Starlette BaseHTTPMiddleware) so that lifespan
  # events pass through to the inner FastMCP Starlette app without interference.
  # ---------------------------------------------------------------------------

  class ApiKeyMiddleware:
      """Enforce Bearer token on /mcp when MCP_API_KEY env var is set.

      - When MCP_API_KEY is unset: all requests pass through (open access).
      - When set: /mcp requests must carry "Authorization: Bearer <key>".
      - /health and all other paths are always exempt.
      """

      def __init__(self, app):
          self.app = app
          self.api_key = os.getenv("MCP_API_KEY")

      async def __call__(self, scope, receive, send):
          if scope["type"] == "http" and self.api_key:
              path = scope.get("path", "")
              if path.startswith("/mcp"):
                  headers = dict(scope.get("headers", []))
                  auth = headers.get(b"authorization", b"").decode("utf-8", errors="replace")
                  if not auth.startswith("Bearer ") or auth[7:] != self.api_key:
                      response = JSONResponse(
                          {"error": "Unauthorized. Provide a valid Bearer token."},
                          status_code=401,
                      )
                      await response(scope, receive, send)
                      return
          await self.app(scope, receive, send)


  # ---------------------------------------------------------------------------
  # App factory
  # ---------------------------------------------------------------------------

  def build_app():
      """Compose the full ASGI stack: FastMCP → auth → CORS."""
      # Stateless mode: each request creates its own transport + server.
      # Required for Cloud Run which may route requests to different replicas.
      app.settings.stateless_http = True

      # FastMCP returns a Starlette app serving /mcp and our custom /health.
      starlette_app = app.streamable_http_app()

      # Wrap with auth (only enforced on /mcp when MCP_API_KEY is set)
      authed = ApiKeyMiddleware(starlette_app)

      # Wrap with CORS — required for claude.ai connectors
      return CORSMiddleware(
          authed,
          allow_origins=["*"],
          allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
          allow_headers=["Content-Type", "Authorization", "Mcp-Session-Id"],
          expose_headers=["Mcp-Session-Id"],
      )


  if __name__ == "__main__":
      api_key = os.getenv("MCP_API_KEY")
      logger.info("Starting TikTok Ads MCP Server (HTTP)")
      logger.info(f"Health: http://0.0.0.0:{PORT}/health")
      logger.info(f"MCP:    http://0.0.0.0:{PORT}/mcp")
      logger.info(f"Auth:   {'ENABLED' if api_key else 'DISABLED'}")
      uvicorn.run(build_app(), host="0.0.0.0", port=PORT)
  ```

- [ ] **Step 5: Install uvicorn locally if needed**

  ```bash
  pip install uvicorn>=0.30.0
  ```

- [ ] **Step 6: Run tests — verify they all pass**

  ```bash
  cd /Users/dhawal/src/tiktok-ads-mcp
  python -m pytest tests/test_server_http.py -v
  ```

  Expected output (all 8 tests pass):
  ```
  tests/test_server_http.py::test_no_api_key_mcp_request_passes PASSED
  tests/test_server_http.py::test_correct_bearer_token_passes PASSED
  tests/test_server_http.py::test_wrong_bearer_token_returns_401 PASSED
  tests/test_server_http.py::test_missing_authorization_header_returns_401 PASSED
  tests/test_server_http.py::test_malformed_authorization_header_returns_401 PASSED
  tests/test_server_http.py::test_health_exempt_from_auth PASSED
  tests/test_server_http.py::test_health_returns_correct_shape PASSED
  tests/test_server_http.py::test_health_auth_disabled_when_no_key PASSED

  8 passed
  ```

  If any test fails, fix `server_http.py` until all 8 pass before proceeding.

- [ ] **Step 7: Smoke-test manually (optional but recommended)**

  ```bash
  # Set dummy creds to bypass TikTokAdsClient validation
  export TIKTOK_APP_ID=test TIKTOK_SECRET=test TIKTOK_ACCESS_TOKEN=test
  python server_http.py &
  sleep 2
  curl -s http://localhost:8080/health | python3 -m json.tool
  # Expected: {"status": "healthy", "service": "tiktok-ads-mcp", ...}
  kill %1
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add server_http.py tests/__init__.py tests/test_server_http.py
  git commit -m "feat: add streamable-HTTP transport (server_http.py) for Cloud Run"
  ```

---

## Task 3: Create `Dockerfile`

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: Create `Dockerfile`**

  ```dockerfile
  # python:3.10-slim chosen over alpine to avoid binary wheel issues
  # with pandas, httpx, and other compiled dependencies.
  FROM python:3.10-slim

  WORKDIR /app

  # Install dependencies first (layer cached unless requirements.txt changes)
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  # Copy application source
  COPY tiktok_ads_mcp/ ./tiktok_ads_mcp/
  COPY server_http.py .

  # Cloud Run injects PORT automatically; default 8080 for local testing
  ENV PORT=8080

  # Run the HTTP server (not the stdio server.py)
  CMD ["python", "server_http.py"]
  ```

- [ ] **Step 2: Build the image locally to verify it works**

  ```bash
  cd /Users/dhawal/src/tiktok-ads-mcp
  docker build -t tiktok-ads-mcp:local .
  ```

  Expected: build completes with `Successfully built ...` and no errors.

- [ ] **Step 3: Run the container locally to smoke-test**

  ```bash
  docker run --rm -p 8080:8080 \
    -e TIKTOK_APP_ID=test \
    -e TIKTOK_SECRET=test \
    -e TIKTOK_ACCESS_TOKEN=test \
    tiktok-ads-mcp:local &

  sleep 3
  curl -s http://localhost:8080/health | python3 -m json.tool
  # Expected: {"status": "healthy", "service": "tiktok-ads-mcp", ...}

  docker stop $(docker ps -q --filter ancestor=tiktok-ads-mcp:local)
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add Dockerfile
  git commit -m "feat: add Dockerfile for Cloud Run deployment (python:3.10-slim)"
  ```

---

## Task 4: Create `cloudbuild.yaml` and `deploy.sh`

**Files:**
- Create: `cloudbuild.yaml`
- Create: `deploy.sh`

- [ ] **Step 1: Create `cloudbuild.yaml`**

  ```yaml
  # Cloud Build pipeline: build image → push → deploy to Cloud Run
  # Trigger this manually or connect to GitHub in the GCP console.
  #
  # Required substitutions (set in Cloud Build trigger or pass with --substitutions):
  #   _REGION    — GCP region, e.g. asia-southeast1
  #   _PROJECT   — GCP project ID, e.g. my-project-123456
  #   _AR_REPO   — Artifact Registry repo name, e.g. mcp-servers
  #
  # Default substitutions below match the ACME deployment target.

  substitutions:
    _REGION: asia-southeast1
    _PROJECT: "YOUR_PROJECT_NUMBER"
    _AR_REPO: mcp-servers
    _SERVICE: tiktok-ads-mcp

  steps:
    # 1. Build the Docker image
    - name: "gcr.io/cloud-builders/docker"
      args:
        - build
        - "-t"
        - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR_REPO}/${_SERVICE}:${COMMIT_SHA}"
        - "-t"
        - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR_REPO}/${_SERVICE}:latest"
        - "."

    # 2. Push both tags to Artifact Registry
    - name: "gcr.io/cloud-builders/docker"
      args:
        - push
        - "--all-tags"
        - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR_REPO}/${_SERVICE}"

    # 3. Deploy to Cloud Run
    - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
      entrypoint: gcloud
      args:
        - run
        - deploy
        - "${_SERVICE}"
        - "--image=${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR_REPO}/${_SERVICE}:${COMMIT_SHA}"
        - "--region=${_REGION}"
        - "--platform=managed"
        - "--allow-unauthenticated"
        - "--port=8080"
        - "--memory=512Mi"
        - "--cpu=1"
        - "--min-instances=0"
        - "--max-instances=3"
        - "--timeout=300"

  images:
    - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR_REPO}/${_SERVICE}:${COMMIT_SHA}"
    - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR_REPO}/${_SERVICE}:latest"
  ```

- [ ] **Step 2: Create `deploy.sh`**

  ```bash
  #!/bin/bash
  # Manual one-shot deploy to Cloud Run (no Cloud Build required).
  # Usage:
  #   ./deploy.sh
  # Prerequisites:
  #   gcloud auth login
  #   gcloud config set project <PROJECT_ID>
  #   Artifact Registry repo must exist:
  #     gcloud artifacts repositories create mcp-servers \
  #       --repository-format=docker --location=asia-southeast1

  set -euo pipefail

  REGION="asia-southeast1"
  PROJECT=$(gcloud config get-value project)
  AR_REPO="mcp-servers"
  SERVICE="tiktok-ads-mcp"
  IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${AR_REPO}/${SERVICE}:latest"

  echo "==> Building image: ${IMAGE}"
  docker build -t "${IMAGE}" .

  echo "==> Configuring Docker for Artifact Registry"
  gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

  echo "==> Pushing image"
  docker push "${IMAGE}"

  echo "==> Deploying to Cloud Run"
  gcloud run deploy "${SERVICE}" \
    --image="${IMAGE}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --timeout=300 \
    --set-env-vars="TIKTOK_APP_ID=${TIKTOK_APP_ID},TIKTOK_SECRET=${TIKTOK_SECRET},TIKTOK_ACCESS_TOKEN=${TIKTOK_ACCESS_TOKEN}"

  echo ""
  echo "==> Deployed. Endpoint:"
  gcloud run services describe "${SERVICE}" \
    --region="${REGION}" \
    --format="value(status.url)"
  ```

  Make it executable:
  ```bash
  chmod +x deploy.sh
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add cloudbuild.yaml deploy.sh
  git commit -m "feat: add Cloud Build pipeline and manual deploy script"
  ```

---

## Task 5: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add Cloud Run deployment section to README**

  Find the end of the existing installation/usage section in `README.md` and add a new section:

  ```markdown
  ## Cloud Run Deployment (Team / Self-Hosted)

  Deploy a shared instance for your team on Google Cloud Run.

  ### Prerequisites

  - Google Cloud project with billing enabled
  - `gcloud` CLI authenticated (`gcloud auth login`)
  - Docker installed locally
  - Artifact Registry repository created:
    ```bash
    gcloud artifacts repositories create mcp-servers \
      --repository-format=docker \
      --location=asia-southeast1 \
      --project=YOUR_PROJECT_ID
    ```

  ### Deploy

  ```bash
  # Set your TikTok credentials
  export TIKTOK_APP_ID=your_app_id
  export TIKTOK_SECRET=your_app_secret
  export TIKTOK_ACCESS_TOKEN=your_access_token

  # Optional: protect the endpoint with a shared team key
  # export MCP_API_KEY=your_team_secret

  # Deploy (builds, pushes, and deploys in one step)
  gcloud config set project YOUR_PROJECT_ID
  ./deploy.sh
  ```

  After deployment, set your secrets permanently in Cloud Run:
  ```bash
  gcloud run services update tiktok-ads-mcp \
    --region=asia-southeast1 \
    --update-env-vars="TIKTOK_APP_ID=...,TIKTOK_SECRET=...,TIKTOK_ACCESS_TOKEN=..."
  ```

  ### Connect Claude

  Add to your Claude Desktop `claude_desktop_config.json` or team connector:

  ```json
  {
    "mcpServers": {
      "tiktok-ads": {
        "url": "https://YOUR_SERVICE_URL/mcp",
        "headers": {
          "Authorization": "Bearer YOUR_MCP_API_KEY"
        }
      }
    }
  }
  ```

  Omit the `headers` block if `MCP_API_KEY` is not set.

  ### Health Check

  ```bash
  curl https://YOUR_SERVICE_URL/health
  # {"status":"healthy","service":"tiktok-ads-mcp","transport":"streamable-http","auth":"enabled"}
  ```

  ### Automated Deployments (Cloud Build)

  Connect `cloudbuild.yaml` to a GitHub trigger in the GCP console to deploy automatically on push to `main`.
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add README.md
  git commit -m "docs: add Cloud Run deployment instructions to README"
  ```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| SSE/HTTP transport | Task 2 — `server_http.py` with streamable-http |
| Dockerfile | Task 3 |
| Updated requirements.txt | Task 1 |
| `cloudbuild.yaml` or deployment script | Task 4 — both |
| `TIKTOK_APP_ID`, `TIKTOK_SECRET`, `TIKTOK_ACCESS_TOKEN` env vars | Already in `config.py`; documented in Task 5 |
| `MCP_API_KEY` optional auth | Task 2 — `ApiKeyMiddleware` |
| Target endpoint `/mcp` | Task 2 — FastMCP defaults `streamable_http_path` to `/mcp` |
| Python 3.10 | Task 1 + Task 3 |
| `/health` endpoint | Task 2 |
| README deployment instructions | Task 5 |

**Placeholder scan:** No TBDs, TODOs, or "similar to Task N" references. All code blocks are complete.

**Type consistency:** `ApiKeyMiddleware` defined once in Task 2 and imported in tests as `from server_http import ApiKeyMiddleware`. The `health` function is also imported directly for unit testing. Names are consistent across all tasks.

**Potential issue — `deploy.sh` project substitution:** `cloudbuild.yaml` uses `_PROJECT: "YOUR_PROJECT_NUMBER"` (the project number). Cloud Run and Artifact Registry typically use project IDs (not numbers). The `deploy.sh` resolves this by using `gcloud config get-value project` which returns the project ID. The README instructs users to `gcloud config set project YOUR_PROJECT_ID`. The `cloudbuild.yaml` substitution `_PROJECT` should be overridden with the actual project ID when setting up the Cloud Build trigger. This is noted in the comments. ✓
