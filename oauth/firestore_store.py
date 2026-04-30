"""
Firestore-backed storage for the embedded OAuth 2.1 authorization server
and per-user TikTok credentials.

Collections (shared with the rest of the team-mcp services where applicable):
  oauth_clients/{client_id}        — DCR client registrations
  oauth_pending/{state}            — pending /oauth/authorize → TikTok round-trip
  oauth_codes/{code}               — issued authorization codes (single-use)
  oauth_tokens/{access_token}      — issued bearer access tokens (1h TTL)
  oauth_refresh/{refresh_token}    — issued refresh tokens (30d TTL)
  user_tokens_tiktok_ads/{key}     — per-user TikTok credentials (key = email or core_user_id)

The first five collections are shared with other team-mcp services; the
tokens are random opaque strings so collisions are impossible. The last
collection is TikTok-specific.
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import httpx
from google.cloud import firestore

logger = logging.getLogger(__name__)

CLIENTS = "oauth_clients"
PENDING = "oauth_pending"
CODES = "oauth_codes"
ACCESS = "oauth_tokens"
REFRESH = "oauth_refresh"
TIKTOK_USERS = "user_tokens_tiktok_ads"

PENDING_TTL = timedelta(minutes=10)
CODE_TTL = timedelta(minutes=10)
ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=30)


def _db():
    return firestore.Client(project=os.environ["GCP_PROJECT_ID"])


def _now():
    return datetime.now(timezone.utc)


def _expired(doc) -> bool:
    exp = doc.get("expires_at")
    if exp is None:
        return False
    if isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp < _now()
    return False


def _new_token(prefix: str, nbytes: int = 32) -> str:
    return f"{prefix}_{secrets.token_urlsafe(nbytes)}"


# ---------- Clients (DCR) ----------

def register_client(redirect_uris: List[str], client_name: str, metadata: dict) -> dict:
    client_id = _new_token("mcp_client", nbytes=16)
    record = {
        "client_id": client_id,
        "redirect_uris": redirect_uris,
        "client_name": client_name,
        "metadata": metadata,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    _db().collection(CLIENTS).document(client_id).set(record)
    return {
        "client_id": client_id,
        "client_id_issued_at": int(_now().timestamp()),
        "redirect_uris": redirect_uris,
        "client_name": client_name,
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        **metadata,
    }


def get_client(client_id: str) -> Optional[dict]:
    doc = _db().collection(CLIENTS).document(client_id).get()
    return doc.to_dict() if doc.exists else None


# ---------- Pending authorizations ----------

def save_pending_authorization(*, state: str, client_id: str, redirect_uri: str, client_state: str,
                               code_challenge: str, code_challenge_method: str,
                               resource: str, scope: str) -> None:
    _db().collection(PENDING).document(state).set({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "client_state": client_state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "resource": resource,
        "scope": scope,
        "expires_at": _now() + PENDING_TTL,
    })


def consume_pending_authorization(state: str) -> Optional[dict]:
    ref = _db().collection(PENDING).document(state)
    doc = ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    ref.delete()
    if _expired(doc):
        return None
    return data


# ---------- Authorization codes ----------

def create_auth_code(*, client_id: str, redirect_uri: str, code_challenge: str,
                     code_challenge_method: str, resource: str, scope: str,
                     user_key: str) -> str:
    code = _new_token("mcp_ac")
    _db().collection(CODES).document(code).set({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "resource": resource,
        "scope": scope,
        "user_key": user_key,
        "expires_at": _now() + CODE_TTL,
    })
    return code


def consume_auth_code(code: str) -> Optional[dict]:
    ref = _db().collection(CODES).document(code)
    doc = ref.get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    ref.delete()
    if _expired(doc):
        return None
    return data


# ---------- Access + refresh tokens (issued by us) ----------

def issue_token_pair(*, client_id: str, user_key: str, resource: str, scope: str) -> dict:
    access = _new_token("mcp_at")
    refresh = _new_token("mcp_rt")
    now = _now()
    _db().collection(ACCESS).document(access).set({
        "client_id": client_id,
        "user_key": user_key,
        "resource": resource,
        "scope": scope,
        "expires_at": now + ACCESS_TTL,
    })
    _db().collection(REFRESH).document(refresh).set({
        "client_id": client_id,
        "user_key": user_key,
        "resource": resource,
        "scope": scope,
        "expires_at": now + REFRESH_TTL,
    })
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": int(ACCESS_TTL.total_seconds()),
        "refresh_token": refresh,
        "scope": scope,
    }


def lookup_access_token(access_token: str) -> Optional[dict]:
    doc = _db().collection(ACCESS).document(access_token).get()
    if not doc.exists or _expired(doc):
        return None
    return doc.to_dict()


def consume_refresh_token(refresh_token: str) -> Optional[dict]:
    """Read-and-rotate: refresh tokens are single use (OAuth 2.1 §4.3.1)."""
    ref = _db().collection(REFRESH).document(refresh_token)
    doc = ref.get()
    if not doc.exists or _expired(doc):
        return None
    data = doc.to_dict()
    ref.delete()
    return data


# ---------- Per-user TikTok credentials ----------

def save_tiktok_tokens(user_key: str, tokens: dict) -> None:
    _db().collection(TIKTOK_USERS).document(user_key).set({
        "tokens": tokens,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })


def load_tiktok_tokens(user_key: str) -> Optional[dict]:
    snap = _db().collection(TIKTOK_USERS).document(user_key).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    return data.get("tokens")


def get_valid_tiktok_access_token(user_key: str) -> Optional[str]:
    """
    Return a valid TikTok access token for the user, refreshing if necessary.

    Returns None if no tokens stored or refresh fails.
    """
    tokens = load_tiktok_tokens(user_key)
    if not tokens:
        return None

    now_sec = int(_now().timestamp())
    expires_at = tokens.get("access_token_expires_at", 0)
    if expires_at > now_sec + 300:
        return tokens.get("access_token")

    refresh = tokens.get("refresh_token")
    if not refresh:
        return None

    app_id = os.environ.get("TIKTOK_APP_ID")
    secret = os.environ.get("TIKTOK_SECRET")
    if not app_id or not secret:
        return None

    try:
        resp = httpx.post(
            "https://business-api.tiktok.com/open_api/v1.3/oauth2/refresh_token/",
            json={"app_id": app_id, "secret": secret, "refresh_token": refresh},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        body = resp.json()
        if body.get("code") != 0:
            logger.warning(f"TikTok token refresh failed: {body.get('message')}")
            return None
        data = body.get("data") or {}
        access = data.get("access_token")
        if not access:
            return None

        # See note in oauth/oauth_server.py — field names vary; fall back to defaults.
        DEFAULT_ACCESS_TTL = 24 * 3600
        access_ttl = int(
            data.get("access_token_expire_in")
            or data.get("access_token_expires_in")
            or data.get("expire_in")
            or DEFAULT_ACCESS_TTL
        )
        old_refresh_remaining = max(0, int(tokens.get("refresh_token_expires_at", 0)) - now_sec)
        refresh_ttl = int(
            data.get("refresh_token_expire_in")
            or data.get("refresh_token_expires_in")
            or old_refresh_remaining
            or 0
        )

        merged = {
            **tokens,
            "access_token": access,
            "refresh_token": data.get("refresh_token") or refresh,
            "access_token_expires_at": now_sec + access_ttl,
            "refresh_token_expires_at": now_sec + refresh_ttl,
            "scope": data.get("scope") or tokens.get("scope"),
            "advertiser_ids": data.get("advertiser_ids") or tokens.get("advertiser_ids"),
        }
        save_tiktok_tokens(user_key, merged)
        return access
    except Exception:
        logger.exception("TikTok token refresh error")
        return None
