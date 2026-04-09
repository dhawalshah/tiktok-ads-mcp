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


# ---------------------------------------------------------------------------
# Task 2: get_video_performance
# ---------------------------------------------------------------------------

def test_get_video_performance_returns_rows_and_page_info():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [{"dimensions": {"ad_id": "A1"}, "metrics": {"play_over_6s": "500"}}],
            "page_info": {"total_number": 1, "page": 1, "page_size": 10},
        },
    }

    from tiktok_ads_mcp.tools.get_video_performance import get_video_performance

    result = asyncio.run(
        get_video_performance(mock_client, advertiser_id="111", start_date="2024-01-01", end_date="2024-01-31")
    )

    assert len(result["list"]) == 1
    assert result["list"][0]["dimensions"]["ad_id"] == "A1"
    assert "page_info" in result
    mock_client._make_request.assert_called_once()
    call_args = mock_client._make_request.call_args
    assert call_args[0][0] == "GET"
    assert call_args[0][1] == "/report/video_performance/get/"
    assert call_args[0][2]["advertiser_id"] == "111"


def test_get_video_performance_dimensions_json_encoded():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": [], "page_info": {}}}

    from tiktok_ads_mcp.tools.get_video_performance import get_video_performance

    asyncio.run(
        get_video_performance(
            mock_client,
            advertiser_id="111",
            dimensions=["ad_id", "stat_time_day"],
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["dimensions"] == json.dumps(["ad_id", "stat_time_day"])


# ---------------------------------------------------------------------------
# Task 3: get_creative_fatigue
# ---------------------------------------------------------------------------

def test_get_creative_fatigue_returns_fatigue_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "ad_id": "AD1",
                    "ad_name": "Summer Sale",
                    "fatigue_status": "HIGH",
                    "fatigue_level": 85,
                    "recommendation": "Refresh creative",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_creative_fatigue import get_creative_fatigue

    result = asyncio.run(get_creative_fatigue(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["ad_id"] == "AD1"
    assert result[0]["fatigue_status"] == "HIGH"
    assert result[0]["recommendation"] == "Refresh creative"


def test_get_creative_fatigue_passes_ad_ids():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_creative_fatigue import get_creative_fatigue

    asyncio.run(get_creative_fatigue(mock_client, advertiser_id="111", ad_ids=["AD1", "AD2"]))

    params = mock_client._make_request.call_args[0][2]
    assert params["ad_ids"] == json.dumps(["AD1", "AD2"])
