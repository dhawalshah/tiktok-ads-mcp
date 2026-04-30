#!/usr/bin/env python3
"""TikTok Ads MCP Server — Streamable HTTP transport for Google Cloud Run.

The /mcp endpoint is an OAuth 2.1 protected resource. The server also acts
as the authorization server for it (see oauth/oauth_server.py), proxying
user authentication to TikTok Business.

Auth flow for MCP clients (Claude, etc.):

  1. Client GETs /mcp without a token → 401 + WWW-Authenticate
  2. Client follows the protected-resource metadata link, registers with
     the authorization server (Dynamic Client Registration), and runs the
     OAuth 2.1 authorization code flow with PKCE.
  3. Client receives an opaque bearer issued by this server and includes
     it on every /mcp request.
  4. Middleware here validates the bearer, looks up the user's stored
     TikTok credentials (refreshing if needed), and exposes the access
     token via a ContextVar consumed by the TikTok API client.
"""

import logging
import os
from importlib.metadata import version as pkg_version, PackageNotFoundError

import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tiktok_ads_mcp.server import app  # FastMCP instance
from tiktok_ads_mcp.config import current_access_token
from oauth import oauth_server, firestore_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT = int(os.getenv("PORT", "8080"))


# ---------------------------------------------------------------------------
# Routes registered on the FastMCP Starlette app via @app.custom_route
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
    })


@app.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    base = (os.getenv("BASE_URL") or "").rstrip("/")
    return JSONResponse({
        "name": "TikTok Ads MCP",
        "mcp_endpoint": f"{base}/mcp" if base else "/mcp",
        "protected_resource_metadata": f"{base}/.well-known/oauth-protected-resource",
    })


# OAuth 2.1 authorization-server endpoints
@app.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def _prm(request: Request):
    return await oauth_server.protected_resource_metadata(request)


@app.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def _asm(request: Request):
    return await oauth_server.authorization_server_metadata(request)


@app.custom_route("/oauth/register", methods=["POST"])
async def _register(request: Request):
    return await oauth_server.oauth_register(request)


@app.custom_route("/oauth/authorize", methods=["GET"])
async def _authorize(request: Request):
    return await oauth_server.oauth_authorize(request)


@app.custom_route("/oauth/callback", methods=["GET"])
async def _callback(request: Request):
    return await oauth_server.oauth_callback(request)


@app.custom_route("/oauth/token", methods=["POST"])
async def _token(request: Request):
    return await oauth_server.oauth_token(request)


# ---------------------------------------------------------------------------
# Auth middleware for /mcp — resolves bearer to user's TikTok access token
# ---------------------------------------------------------------------------

class BearerAuthMiddleware:
    """OAuth 2.1 bearer authentication for /mcp requests.

    Resolves our opaque bearer to the stored TikTok access token (refreshing
    via TikTok's refresh-token endpoint if expired) and sets the
    `current_access_token` ContextVar consumed by the API client.

    Returns 401 + WWW-Authenticate per RFC 9728 if no valid bearer.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not (path == "/mcp" or path.startswith("/mcp/")):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth = headers.get(b"authorization", b"").decode("utf-8", errors="replace")
        if not auth.lower().startswith("bearer "):
            await self._unauthorized(scope, receive, send)
            return

        access_token = auth.split(" ", 1)[1].strip()
        record = oauth_server.resolve_bearer(access_token)
        if not record:
            await self._unauthorized(scope, receive, send)
            return

        user_key = record.get("user_key")
        if not user_key:
            await self._unauthorized(scope, receive, send)
            return

        tiktok_token = firestore_store.get_valid_tiktok_access_token(user_key)
        if not tiktok_token:
            # User's TikTok credentials are missing or unrefreshable —
            # force the client back through the OAuth dance.
            await self._unauthorized(scope, receive, send)
            return

        token_ctx = current_access_token.set(tiktok_token)
        try:
            await self.app(scope, receive, send)
        finally:
            current_access_token.reset(token_ctx)

    async def _unauthorized(self, scope, receive, send):
        base = (os.getenv("BASE_URL") or "").rstrip("/")
        metadata_url = f"{base}/.well-known/oauth-protected-resource"
        response = Response(
            content='{"error":"unauthorized"}',
            status_code=401,
            media_type="application/json",
            headers={
                "WWW-Authenticate": (
                    f'Bearer realm="mcp", '
                    f'resource_metadata="{metadata_url}", '
                    f'error="invalid_token"'
                )
            },
        )
        await response(scope, receive, send)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def build_app():
    """Compose the full ASGI stack: FastMCP → bearer auth → CORS."""
    # Stateless mode: each request creates its own transport + server.
    # Required for Cloud Run which may route requests to different replicas.
    app.settings.stateless_http = True

    # FastMCP returns a Starlette app serving /mcp and our custom routes.
    starlette_app = app.streamable_http_app()

    # Wrap with OAuth bearer auth (only enforced on /mcp)
    authed = BearerAuthMiddleware(starlette_app)

    # Wrap with CORS — required for claude.ai connectors
    return CORSMiddleware(
        authed,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Mcp-Session-Id"],
        expose_headers=["Mcp-Session-Id"],
    )


if __name__ == "__main__":
    logger.info("Starting TikTok Ads MCP Server (HTTP)")
    logger.info(f"Health: http://0.0.0.0:{PORT}/health")
    logger.info(f"MCP:    http://0.0.0.0:{PORT}/mcp")
    uvicorn.run(build_app(), host="0.0.0.0", port=PORT)
