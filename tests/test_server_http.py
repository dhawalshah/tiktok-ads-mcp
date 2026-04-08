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
    """Return a minimal Starlette app with one route at `path`."""
    async def handler(request):
        return PlainTextResponse("ok")

    return Starlette(routes=[Route(path, handler, methods=["GET", "POST", "DELETE"])])


def _make_middleware(api_key, inner=None):
    """Instantiate ApiKeyMiddleware with the given MCP_API_KEY env value."""
    from server_http import ApiKeyMiddleware

    inner = inner or _mock_inner()
    env = {"MCP_API_KEY": api_key} if api_key else {}
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
