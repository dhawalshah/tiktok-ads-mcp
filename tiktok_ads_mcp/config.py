"""Configuration management for TikTok Ads MCP Server.

Supports two modes:
  * STDIO/local single-user: TIKTOK_ACCESS_TOKEN env var carries the user's
    own token (fetched via get_token.py / catch_auth.py).
  * HTTP server / Cloud Run multi-user: each request resolves a per-user
    access token from Firestore via the OAuth 2.1 flow and exposes it
    through the `current_access_token` ContextVar set by server_http.py.

The config below treats TIKTOK_ACCESS_TOKEN as optional. When the
ContextVar is set, the client uses that. When neither is available the
client raises a helpful error.
"""

import contextvars
import os
from typing import Dict, Any, List

from dotenv import load_dotenv
load_dotenv()


# Set per-request by the HTTP server's bearer middleware. Empty/None in
# STDIO mode — falls back to TIKTOK_ACCESS_TOKEN env var.
current_access_token: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_access_token", default=""
)


class TikTokConfig:
    """Configuration class for TikTok Business API"""

    # TikTok API Configuration
    APP_ID: str = os.getenv("TIKTOK_APP_ID", "")
    SECRET: str = os.getenv("TIKTOK_SECRET", "")
    ACCESS_TOKEN: str = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    ADVERTISER_ID: str = os.getenv("TIKTOK_ADVERTISER_ID", "")
    SANDBOX: bool = os.getenv("TIKTOK_SANDBOX", "false").lower() == "true"

    # API URLs
    BASE_URL: str = "https://business-api.tiktok.com/open_api" if not SANDBOX else "https://sandbox-ads.tiktok.com/open_api"
    API_VERSION: str = "v1.3"

    # Request Configuration
    REQUEST_TIMEOUT: int = int(os.getenv("TIKTOK_REQUEST_TIMEOUT", "30"))  # seconds

    @classmethod
    def get_access_token(cls) -> str:
        """Resolve the access token to use for the current request.

        Prefers the per-request ContextVar (HTTP server mode); falls back
        to the TIKTOK_ACCESS_TOKEN env var (STDIO/local mode).
        """
        token = current_access_token.get()
        if token:
            return token
        return cls.ACCESS_TOKEN

    @classmethod
    def validate_credentials(cls) -> bool:
        """Validate that all required credentials are present for this request."""
        if not cls.APP_ID.strip() or not cls.SECRET.strip():
            return False
        return bool(cls.get_access_token().strip())

    @classmethod
    def get_missing_credentials(cls) -> List[str]:
        """Get list of missing credential fields"""
        missing = []
        if not cls.APP_ID.strip():
            missing.append("TIKTOK_APP_ID")
        if not cls.SECRET.strip():
            missing.append("TIKTOK_SECRET")
        if not cls.get_access_token().strip():
            missing.append("TIKTOK_ACCESS_TOKEN (or per-user OAuth token)")
        return missing

    @classmethod
    def get_health_info(cls) -> Dict[str, Any]:
        """Get system health information"""
        return {
            "config_valid": cls.validate_credentials(),
            "base_url": cls.BASE_URL,
            "api_version": cls.API_VERSION,
        }


# Global config instance
config = TikTokConfig()
