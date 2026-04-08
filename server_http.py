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
from importlib.metadata import version as pkg_version, PackageNotFoundError

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
    try:
        _version = pkg_version("tiktok-ads-mcp")
    except PackageNotFoundError:
        _version = "dev"
    return JSONResponse({
        "status": "healthy",
        "service": "tiktok-ads-mcp",
        "version": _version,
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
