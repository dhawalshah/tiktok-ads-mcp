"""
OAuth 2.1 authorization server endpoints for the TikTok Ads MCP.

Implements the subset required by the MCP authorization spec
(2025-06-18): RFC 9728 (Protected Resource Metadata), RFC 8414
(Authorization Server Metadata), RFC 7591 (Dynamic Client Registration),
RFC 8707 (Resource Indicators), and OAuth 2.1 PKCE.

The MCP server proxies OAuth: Claude (the MCP client) talks OAuth to us;
we delegate the actual user identification to TikTok. TikTok credentials
never leave the server — Claude only sees opaque tokens we issue.

Notes on TikTok specifics:
  * TikTok's Business OAuth flow does not accept PKCE on the upstream side,
    so we use plain authorization-code flow with a `state` parameter to
    TikTok. PKCE is enforced on the Claude → us side.
  * TikTok's token endpoint expects a JSON body with `app_id`, `secret`,
    `auth_code` (not the standard form-encoded `client_id`/`code`). The
    response is wrapped: `{"code": 0, "data": {...}}`.
  * The TikTok access token is sent as an `Access-Token` header (not
    `Authorization: Bearer`).
"""

import os
import base64
import hashlib
import hmac
import logging
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse

from .firestore_store import (
    register_client,
    get_client,
    save_pending_authorization,
    consume_pending_authorization,
    create_auth_code,
    consume_auth_code,
    issue_token_pair,
    lookup_access_token,
    consume_refresh_token,
    save_tiktok_tokens,
)

logger = logging.getLogger(__name__)

TIKTOK_AUTHORIZE_URL = "https://business-api.tiktok.com/portal/auth"
TIKTOK_TOKEN_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
TIKTOK_USERINFO_URL = "https://business-api.tiktok.com/open_api/v1.3/user/info/"

# Scopes we advertise to MCP clients (opaque to TikTok — protocol-level).
ADVERTISED_SCOPES = ["tiktok.ads"]


def _base_url() -> str:
    return os.environ["BASE_URL"].rstrip("/")


def _canonical_resource() -> str:
    return f"{_base_url()}/mcp"


def _tiktok_redirect_uri() -> str:
    return os.environ.get("TIKTOK_REDIRECT_URI") or f"{_base_url()}/oauth/callback"


def _tiktok_app_id() -> str:
    v = os.environ.get("TIKTOK_APP_ID")
    if not v:
        raise RuntimeError("TIKTOK_APP_ID is not set")
    return v


def _tiktok_secret() -> str:
    v = os.environ.get("TIKTOK_SECRET")
    if not v:
        raise RuntimeError("TIKTOK_SECRET is not set")
    return v


def _allowed_emails() -> list:
    raw = (os.environ.get("ALLOWED_EMAILS") or "").strip()
    if not raw:
        return []
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def _verify_pkce(verifier: str, challenge: str, method: str) -> bool:
    if method != "S256":
        return False
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, challenge)


def _oauth_error(error: str, description: str = "", status: int = 400) -> JSONResponse:
    body = {"error": error}
    if description:
        body["error_description"] = description
    return JSONResponse(body, status_code=status)


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )


# ---------- Discovery ----------

async def protected_resource_metadata(request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": _canonical_resource(),
        "authorization_servers": [_base_url()],
        "scopes_supported": ADVERTISED_SCOPES,
        "bearer_methods_supported": ["header"],
    })


async def authorization_server_metadata(request: Request) -> JSONResponse:
    base = _base_url()
    return JSONResponse({
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "registration_endpoint": f"{base}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ADVERTISED_SCOPES,
    })


# ---------- Dynamic Client Registration ----------

async def oauth_register(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _oauth_error("invalid_client_metadata", "Body must be JSON")

    redirect_uris = body.get("redirect_uris")
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return _oauth_error("invalid_redirect_uri", "redirect_uris must be a non-empty array")

    for uri in redirect_uris:
        if not isinstance(uri, str):
            return _oauth_error("invalid_redirect_uri", "redirect_uris must be strings")
        if not (uri.startswith("https://") or uri.startswith("http://localhost") or uri.startswith("http://127.0.0.1")):
            return _oauth_error("invalid_redirect_uri", f"redirect_uri must be https or localhost: {uri}")

    client_name = body.get("client_name", "Unnamed MCP Client")
    metadata = {k: v for k, v in body.items() if k not in {"redirect_uris", "client_name"}}

    record = register_client(redirect_uris, client_name, metadata)
    logger.info(f"Registered OAuth client {record['client_id']} ({client_name})")
    return JSONResponse(record, status_code=201)


# ---------- /oauth/authorize ----------

async def oauth_authorize(request: Request) -> "RedirectResponse | JSONResponse":
    qp = request.query_params
    response_type = qp.get("response_type", "")
    client_id = qp.get("client_id", "")
    redirect_uri = qp.get("redirect_uri", "")
    code_challenge = qp.get("code_challenge", "")
    code_challenge_method = qp.get("code_challenge_method", "")
    client_state = qp.get("state", "")
    scope = qp.get("scope", " ".join(ADVERTISED_SCOPES))
    requested_resource = qp.get("resource", "")

    if response_type != "code":
        return _oauth_error("unsupported_response_type", "Only 'code' is supported")
    if not client_id:
        return _oauth_error("invalid_request", "client_id is required")

    client = get_client(client_id)
    if not client:
        return _oauth_error("invalid_client", "Unknown client_id", status=401)
    if not redirect_uri or redirect_uri not in client["redirect_uris"]:
        return _oauth_error("invalid_request", "redirect_uri not registered")
    if not code_challenge or code_challenge_method != "S256":
        return _oauth_error("invalid_request", "PKCE with S256 is required")

    canonical = _canonical_resource()
    if requested_resource and requested_resource.rstrip("/") != canonical.rstrip("/"):
        return _oauth_error("invalid_target", f"resource must be {canonical}")

    our_state = secrets.token_urlsafe(32)
    save_pending_authorization(
        state=our_state,
        client_id=client_id,
        redirect_uri=redirect_uri,
        client_state=client_state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=canonical,
        scope=scope,
    )

    params = {
        "app_id": _tiktok_app_id(),
        "redirect_uri": _tiktok_redirect_uri(),
        "state": our_state,
    }
    return RedirectResponse(f"{TIKTOK_AUTHORIZE_URL}?{urlencode(params)}")


# ---------- /oauth/callback (TikTok redirects here) ----------

async def oauth_callback(request: Request) -> "RedirectResponse | HTMLResponse":
    qp = request.query_params
    auth_code = qp.get("auth_code") or qp.get("code")
    state = qp.get("state", "")
    error_msg = qp.get("error_description") or qp.get("error")

    if error_msg:
        return HTMLResponse(
            f"<h2>TikTok login cancelled</h2><p>{_escape(error_msg)}</p>",
            status_code=400,
        )
    if not state or not auth_code:
        return HTMLResponse("<h2>Missing state or auth_code</h2>", status_code=400)

    pending = consume_pending_authorization(state)
    if not pending:
        return HTMLResponse(
            "<h2>This authorization request has expired or already been used.</h2>"
            "<p>Please retry the connect flow from your MCP client.</p>",
            status_code=400,
        )

    # Exchange auth_code for tokens (TikTok-specific JSON body)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                TIKTOK_TOKEN_URL,
                json={
                    "app_id": _tiktok_app_id(),
                    "secret": _tiktok_secret(),
                    "auth_code": auth_code,
                },
                headers={"Content-Type": "application/json"},
            )
            body = resp.json()
    except Exception as e:
        logger.exception("TikTok token exchange failed")
        return HTMLResponse(
            f"<h2>TikTok token exchange failed</h2><p>{_escape(str(e))}</p>",
            status_code=502,
        )

    if body.get("code") != 0:
        return HTMLResponse(
            f"<h2>TikTok token exchange rejected</h2><p>{_escape(str(body))}</p>",
            status_code=502,
        )

    data = body.get("data") or {}
    access = data.get("access_token")
    if not access:
        return HTMLResponse("<h2>TikTok did not return an access token.</h2>", status_code=502)

    # TikTok's response has used different field names across docs/versions —
    # check several candidates and fall back to a 24h default for access token,
    # 1 year default for refresh token (matching their typical lifetimes).
    DEFAULT_ACCESS_TTL = 24 * 3600
    DEFAULT_REFRESH_TTL = 365 * 24 * 3600
    access_ttl = int(
        data.get("access_token_expire_in")
        or data.get("access_token_expires_in")
        or data.get("expire_in")
        or DEFAULT_ACCESS_TTL
    )
    refresh_ttl = int(
        data.get("refresh_token_expire_in")
        or data.get("refresh_token_expires_in")
        or DEFAULT_REFRESH_TTL
    )
    logger.info(f"TikTok token response keys: {list(data.keys())}, access_ttl={access_ttl}s")

    now_sec = int(__import__("time").time())
    tokens = {
        "access_token": access,
        "refresh_token": data.get("refresh_token"),
        "access_token_expires_at": now_sec + access_ttl,
        "refresh_token_expires_at": now_sec + refresh_ttl,
        "scope": data.get("scope"),
        "advertiser_ids": data.get("advertiser_ids"),
    }

    # Identify the user via TikTok's user info endpoint
    email = ""
    core_user_id = ""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            ui_resp = await client.get(
                TIKTOK_USERINFO_URL,
                headers={"Access-Token": access},
            )
            ui_body = ui_resp.json()
            if ui_body.get("code") == 0:
                ui_data = ui_body.get("data") or {}
                email = (ui_data.get("email") or "").lower()
                core_user_id = str(ui_data.get("core_user_id") or "")
    except Exception:
        logger.exception("TikTok userinfo fetch failed")

    user_key = email or (f"core_user_{core_user_id}" if core_user_id else "")
    if not user_key:
        return HTMLResponse(
            "<h2>Could not identify your TikTok user.</h2>"
            "<p>The token exchange succeeded but neither email nor core_user_id was returned.</p>",
            status_code=502,
        )

    # Optional email allow-list (off by default; TikTok auth alone is the gate)
    allow = _allowed_emails()
    if allow and (not email or email not in allow):
        return HTMLResponse(
            f"<h2>Access denied</h2>"
            f"<p>The TikTok email <strong>{_escape(email or '(unknown)')}</strong> is not on the allow-list.</p>",
            status_code=403,
        )

    save_tiktok_tokens(user_key, tokens)
    logger.info(f"Stored TikTok credentials for {user_key}")

    our_code = create_auth_code(
        client_id=pending["client_id"],
        redirect_uri=pending["redirect_uri"],
        code_challenge=pending["code_challenge"],
        code_challenge_method=pending["code_challenge_method"],
        resource=pending["resource"],
        scope=pending["scope"],
        user_key=user_key,
    )

    params = {"code": our_code}
    if pending.get("client_state"):
        params["state"] = pending["client_state"]
    sep = "&" if "?" in pending["redirect_uri"] else "?"
    return RedirectResponse(f"{pending['redirect_uri']}{sep}{urlencode(params)}")


# ---------- /oauth/token ----------

async def oauth_token(request: Request) -> JSONResponse:
    form = await request.form()
    grant_type = form.get("grant_type")

    if grant_type == "authorization_code":
        code = form.get("code")
        client_id = form.get("client_id")
        redirect_uri = form.get("redirect_uri")
        code_verifier = form.get("code_verifier")
        requested_resource = form.get("resource")
        if not code or not client_id or not redirect_uri or not code_verifier:
            return _oauth_error("invalid_request", "Missing required fields")
        record = consume_auth_code(code)
        if not record:
            return _oauth_error("invalid_grant", "Authorization code invalid or expired")
        if record["client_id"] != client_id:
            return _oauth_error("invalid_grant", "client_id does not match")
        if record["redirect_uri"] != redirect_uri:
            return _oauth_error("invalid_grant", "redirect_uri does not match")
        if not _verify_pkce(code_verifier, record["code_challenge"], record["code_challenge_method"]):
            return _oauth_error("invalid_grant", "PKCE verification failed")
        canonical = _canonical_resource()
        if requested_resource and str(requested_resource).rstrip("/") != canonical.rstrip("/"):
            return _oauth_error("invalid_target", f"resource must be {canonical}")
        pair = issue_token_pair(
            client_id=client_id,
            user_key=record["user_key"],
            resource=record["resource"],
            scope=record["scope"],
        )
        return JSONResponse(pair)

    if grant_type == "refresh_token":
        refresh_token = form.get("refresh_token")
        client_id = form.get("client_id")
        if not refresh_token or not client_id:
            return _oauth_error("invalid_request", "Missing required fields")
        record = consume_refresh_token(refresh_token)
        if not record:
            return _oauth_error("invalid_grant", "Refresh token invalid or expired")
        if record["client_id"] != client_id:
            return _oauth_error("invalid_grant", "client_id does not match")
        pair = issue_token_pair(
            client_id=client_id,
            user_key=record["user_key"],
            resource=record["resource"],
            scope=record["scope"],
        )
        return JSONResponse(pair)

    return _oauth_error("unsupported_grant_type", f"Unsupported grant_type: {grant_type}")


# ---------- Bearer resolution (used by /mcp middleware) ----------

def resolve_bearer(access_token: str) -> Optional[dict]:
    record = lookup_access_token(access_token)
    if not record:
        return None
    if (record.get("resource", "") or "").rstrip("/") != _canonical_resource().rstrip("/"):
        return None
    return record
