"""Unit tests for new TikTok Ads MCP tools (Tasks 1–9).

Each test mocks client._make_request and calls the tool function directly.
Uses asyncio.run() — no pytest-asyncio needed.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Task 1: get_advertiser_info
# ---------------------------------------------------------------------------

def test_get_advertiser_info_returns_advertisers():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "advertiser_id": "111",
                    "name": "Test Co",
                    "currency": "USD",
                    "timezone": "America/New_York",
                    "industry": "ECOMMERCE",
                    "status": "STATUS_ENABLE",
                    "description": "desc",
                    "phone_number": "555",
                    "address": "addr",
                    "contacter": "Jane",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_advertiser_info import get_advertiser_info

    result = asyncio.run(get_advertiser_info(mock_client, advertiser_ids=["111"]))

    assert len(result) == 1
    assert result[0]["advertiser_id"] == "111"
    assert result[0]["currency"] == "USD"
    assert result[0]["timezone"] == "America/New_York"
    mock_client._make_request.assert_called_once_with(
        "GET", "/advertiser/info/", {"advertiser_ids": json.dumps(["111"])}
    )


def test_get_advertiser_info_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_advertiser_info import get_advertiser_info

    result = asyncio.run(get_advertiser_info(mock_client, advertiser_ids=[]))
    assert result == []
