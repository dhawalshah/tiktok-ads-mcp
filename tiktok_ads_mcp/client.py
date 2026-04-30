"""TikTok Ads API Client for MCP Server"""

import httpx
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlencode
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import config

# Set up logging
logger = logging.getLogger(__name__)

class TikTokAdsClient:
    """TikTok Business API client for campaign operations."""
    
    def __init__(self):
        """Initialize TikTok API client"""
        # Validate credentials on initialization
        if not config.validate_credentials():
            missing = config.get_missing_credentials()
            raise Exception(
                f"Missing required credentials: {', '.join(missing)}. "
                f"Please check your configuration and ensure all required fields are set."
            )

        self.app_id = config.APP_ID
        self.secret = config.SECRET
        self.base_url = config.BASE_URL
        self.api_version = config.API_VERSION
        self.request_timeout = config.REQUEST_TIMEOUT

        logger.info("TikTok API client initialized")

    @property
    def access_token(self) -> str:
        """Resolve the access token at call time.

        In HTTP server mode this returns the per-request token set by the
        bearer middleware (different per user). In STDIO mode it returns
        the static TIKTOK_ACCESS_TOKEN env var.
        """
        return config.get_access_token()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True
    )
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to TikTok API with proper authentication handling"""
        
        # Prepare parameters
        if params is None:
            params = {}
        
        # Add app_id and secret ONLY for oauth2 endpoints
        if 'oauth2' in endpoint:
            params.update({
                'app_id': self.app_id,
                'secret': self.secret
            })
        
        # Construct URL
        if params:
            query_string = urlencode(params)
            url = f"{self.base_url}/{self.api_version}/{endpoint}?{query_string}"
        else:
            url = f"{self.base_url}/{self.api_version}/{endpoint}"
        
        headers = {
            'Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            try:
                logger.debug(f"Making {method} request to {url}")
                logger.debug(f"Parameters: {params}")
                logger.debug(f"Headers: {headers}")
                
                if method == 'GET':
                    response = await client.get(url, headers=headers)
                elif method == 'POST':
                    response = await client.post(url, json=data, headers=headers)
                else:
                    raise Exception(f"Unsupported HTTP method: {method}")
                
                logger.debug(f"Response status: {response.status_code}")
                # logger.debug(f"Response text: {response.text}") # Commented out to avoid log spam
                
                # Handle HTTP errors
                if response.status_code == 401:
                    raise Exception("Invalid access token or credentials")
                elif response.status_code == 403:
                    raise Exception("Access forbidden - check your API permissions")
                elif response.status_code == 429:
                    # Raise HTTPStatusError to trigger retry
                    response.raise_for_status()
                elif response.status_code >= 400:
                    response.raise_for_status()
                
                # Parse response
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    raise Exception(f"Invalid JSON response: {response.text}")
                
                # Check TikTok API response code
                if result.get('code') != 0:
                    error_msg = result.get('message', 'Unknown API error')
                    raise Exception(f"TikTok API error {result.get('code')}: {error_msg}")
                
                return result
                
            except httpx.TimeoutException:
                raise Exception(f"Request timeout after {self.request_timeout} seconds")
            except httpx.RequestError as e:
                raise Exception(f"Connection error: {str(e)}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise # Let retry handle it
                raise Exception(f"HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                raise Exception(f"Unexpected error: {str(e)}")