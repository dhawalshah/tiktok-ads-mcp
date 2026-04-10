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
        get_video_performance(
            mock_client,
            advertiser_id="111",
            campaign_ids=["C1"],
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    )

    assert len(result["list"]) == 1
    assert result["list"][0]["dimensions"]["ad_id"] == "A1"
    assert "page_info" in result
    mock_client._make_request.assert_called_once()
    call_args = mock_client._make_request.call_args
    assert call_args[0][0] == "GET"
    assert call_args[0][1] == "/report/video_performance/get/"
    assert call_args[0][2]["advertiser_id"] == "111"
    assert json.loads(call_args[0][2]["filtering"]) == {"campaign_ids": ["C1"]}


def test_get_video_performance_dimensions_json_encoded():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": [], "page_info": {}}}

    from tiktok_ads_mcp.tools.get_video_performance import get_video_performance

    asyncio.run(
        get_video_performance(
            mock_client,
            advertiser_id="111",
            ad_ids=["AD1"],
            dimensions=["ad_id", "stat_time_day"],
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["dimensions"] == json.dumps(["ad_id", "stat_time_day"])
    assert json.loads(params["filtering"]) == {"ad_ids": ["AD1"]}


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


# ---------------------------------------------------------------------------
# Task 4: get_ad_benchmark
# ---------------------------------------------------------------------------

def test_get_ad_benchmark_returns_benchmark_dict():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "compare_date": "2024-01-31",
            "items": [{"info": {"ad_id": "AD1"}, "metrics": {"ctr": "1.5"}}],
        },
    }

    from tiktok_ads_mcp.tools.get_ad_benchmark import get_ad_benchmark

    result = asyncio.run(get_ad_benchmark(mock_client, advertiser_id="111", ad_ids=["AD1"]))

    assert "items" in result
    assert result["items"][0]["info"]["ad_id"] == "AD1"


def test_get_ad_benchmark_passes_required_params():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {}}

    from tiktok_ads_mcp.tools.get_ad_benchmark import get_ad_benchmark

    asyncio.run(
        get_ad_benchmark(
            mock_client,
            advertiser_id="111",
            ad_ids=["AD1", "AD2"],
            dimensions=["PLACEMENT"],
            objective_type="CONVERSIONS",
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert json.loads(params["dimensions"]) == ["PLACEMENT"]
    assert json.loads(params["filtering"]) == {"ad_ids": ["AD1", "AD2"]}
    assert params["objective_type"] == "CONVERSIONS"


# ---------------------------------------------------------------------------
# Task 5: async_reports (create / check / download)
# ---------------------------------------------------------------------------

def test_create_async_report_returns_task_id():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {"task_id": "TASK_001"},
    }

    from tiktok_ads_mcp.tools.async_reports import create_async_report

    result = asyncio.run(
        create_async_report(
            mock_client,
            advertiser_id="111",
            report_type="BASIC",
            data_level="AUCTION_AD",
            dimensions=["ad_id", "stat_time_day"],
            metrics=["spend", "impressions"],
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    )

    assert result["task_id"] == "TASK_001"
    assert result["status"] == "PROCESSING"
    # Verify it used POST with data body
    call_args = mock_client._make_request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "/report/task/create/"
    body = call_args[1]["data"]
    assert body["advertiser_id"] == "111"
    assert body["metrics"] == ["spend", "impressions"]


def test_check_async_report_returns_status():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {"task_id": "TASK_001", "status": "COMPLETE", "progress_rate": 100},
    }

    from tiktok_ads_mcp.tools.async_reports import check_async_report

    result = asyncio.run(check_async_report(mock_client, advertiser_id="111", task_id="TASK_001"))

    assert result["task_id"] == "TASK_001"
    assert result["status"] == "COMPLETE"
    assert result["progress_rate"] == 100
    call_args = mock_client._make_request.call_args[0]
    assert call_args[0] == "GET"
    assert call_args[2]["task_id"] == "TASK_001"


def test_download_async_report_inline_rows():
    """When API returns rows directly (no URL), return them."""
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {"list": [{"dimensions": {}, "metrics": {"spend": "100"}}]},
    }

    from tiktok_ads_mcp.tools.async_reports import download_async_report

    result = asyncio.run(download_async_report(mock_client, advertiser_id="111", task_id="TASK_001"))

    assert result == [{"dimensions": {}, "metrics": {"spend": "100"}}]


def test_download_async_report_follows_download_url():
    """When API returns a download_url, fetch it and return JSON rows."""
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {"download_url": "https://example.com/report.json"},
    }

    mock_http_response = MagicMock()
    mock_http_response.raise_for_status = MagicMock()
    mock_http_response.json.return_value = [{"row": 1}]
    mock_http_response.text = '[{"row": 1}]'

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_http_response

    with patch("tiktok_ads_mcp.tools.async_reports.httpx.AsyncClient") as MockClass:
        MockClass.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
        MockClass.return_value.__aexit__ = AsyncMock(return_value=None)

        from tiktok_ads_mcp.tools.async_reports import download_async_report

        result = asyncio.run(download_async_report(mock_client, advertiser_id="111", task_id="TASK_001"))

    assert result == [{"row": 1}]
    mock_http_client.get.assert_called_once_with("https://example.com/report.json")


# ---------------------------------------------------------------------------
# Task 6: get_audience_reach
# ---------------------------------------------------------------------------

def test_get_audience_reach_returns_size_estimate():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "lower": 500000,
            "upper": 1200000,
            "reach_trend": [{"date": "2024-01-01", "reach": 600000}],
        },
    }

    from tiktok_ads_mcp.tools.get_audience_reach import get_audience_reach

    result = asyncio.run(
        get_audience_reach(
            mock_client,
            advertiser_id="111",
            objective_type="TRAFFIC",
            location_ids=["US"],
        )
    )

    assert result["estimated_audience_size_lower"] == 500000
    assert result["estimated_audience_size_upper"] == 1200000
    assert "reach_trend" in result
    # Verify POST with body containing advertiser_id and objective_type
    call_args = mock_client._make_request.call_args
    assert call_args[0][0] == "POST"
    body = call_args[1]["data"]
    assert body["advertiser_id"] == "111"
    assert body["objective_type"] == "TRAFFIC"
    assert body["location_ids"] == ["US"]


def test_get_audience_reach_omits_none_targeting():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {}}

    from tiktok_ads_mcp.tools.get_audience_reach import get_audience_reach

    asyncio.run(get_audience_reach(mock_client, advertiser_id="111", objective_type="TRAFFIC"))

    body = mock_client._make_request.call_args[1]["data"]
    assert "age" not in body
    assert "gender" not in body
    assert "placements" not in body


# ---------------------------------------------------------------------------
# Task 7: get_targeting_options
# ---------------------------------------------------------------------------

def test_get_targeting_options_returns_options_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "interest_categories": [
                {
                    "interest_category_id": "10",
                    "interest_category_name": "Education",
                    "level": 1,
                    "sub_category_ids": ["10100", "10101"],
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_targeting_options import get_targeting_options

    result = asyncio.run(get_targeting_options(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["id"] == "10"
    assert result[0]["name"] == "Education"
    assert result[0]["level"] == 1
    assert result[0]["sub_category_ids"] == ["10100", "10101"]
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"


def test_get_targeting_options_passes_objective_type():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"interest_categories": []}}

    from tiktok_ads_mcp.tools.get_targeting_options import get_targeting_options

    asyncio.run(
        get_targeting_options(mock_client, advertiser_id="111", objective_type="TRAFFIC")
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["objective_type"] == "TRAFFIC"
    assert "query" not in params


# ---------------------------------------------------------------------------
# Task 8: get_pixels
# ---------------------------------------------------------------------------

def test_get_pixels_returns_pixel_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "pixel_id": "PX1",
                    "pixel_name": "Main Site",
                    "pixel_code": "ABCDEF",
                    "status": "NORMAL",
                    "create_time": "2023-01-01",
                    "events": ["Purchase", "ViewContent"],
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_pixels import get_pixels

    result = asyncio.run(get_pixels(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["pixel_id"] == "PX1"
    assert result[0]["events"] == ["Purchase", "ViewContent"]
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"
    assert params["page"] == 1
    assert params["page_size"] == 20


def test_get_pixels_respects_pagination():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_pixels import get_pixels

    asyncio.run(get_pixels(mock_client, advertiser_id="111", page=2, page_size=5))

    params = mock_client._make_request.call_args[0][2]
    assert params["page"] == 2
    assert params["page_size"] == 5


# ---------------------------------------------------------------------------
# Task 9: get_smart_plus_campaigns
# ---------------------------------------------------------------------------

def test_get_smart_plus_campaigns_returns_campaign_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "campaign_id": "SPC1",
                    "campaign_name": "Smart+ Q1",
                    "status": "ENABLE",
                    "budget": "500.00",
                    "budget_mode": "BUDGET_MODE_DAY",
                    "objective_type": "CONVERSIONS",
                    "create_time": "2024-01-01",
                    "modify_time": "2024-02-01",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_smart_plus_campaigns import get_smart_plus_campaigns

    result = asyncio.run(get_smart_plus_campaigns(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["campaign_id"] == "SPC1"
    assert result[0]["objective_type"] == "CONVERSIONS"
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"


def test_get_smart_plus_campaigns_filters_by_ids():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_smart_plus_campaigns import get_smart_plus_campaigns

    asyncio.run(
        get_smart_plus_campaigns(
            mock_client,
            advertiser_id="111",
            campaign_ids=["SPC1", "SPC2"],
            status="ENABLE",
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["campaign_ids"] == json.dumps(["SPC1", "SPC2"])
    assert params["status"] == "ENABLE"


# ---------------------------------------------------------------------------
# get_pixel_event_stats
# ---------------------------------------------------------------------------

def test_get_pixel_event_stats_returns_event_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "pixel_id": "PX1",
                    "event_type": "Purchase",
                    "date": "2024-01-01",
                    "count": 42,
                    "match_rate": 0.85,
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_pixel_event_stats import get_pixel_event_stats

    result = asyncio.run(
        get_pixel_event_stats(
            mock_client,
            advertiser_id="111",
            pixel_ids=["PX1"],
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    )

    assert len(result) == 1
    assert result[0]["pixel_id"] == "PX1"
    assert result[0]["event_type"] == "Purchase"
    assert result[0]["count"] == 42
    assert result[0]["match_rate"] == 0.85
    assert result[0]["date"] == "2024-01-01"
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"
    assert params["pixel_ids"] == json.dumps(["PX1"])
    assert params["start_date"] == "2024-01-01"
    assert params["end_date"] == "2024-01-31"


def test_get_pixel_event_stats_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_pixel_event_stats import get_pixel_event_stats

    result = asyncio.run(
        get_pixel_event_stats(
            mock_client,
            advertiser_id="111",
            pixel_ids=["PX1"],
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    )
    assert result == []

# ---------------------------------------------------------------------------
# get_video_assets
# ---------------------------------------------------------------------------

def test_get_video_assets_returns_video_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "videos": [
                {
                    "video_id": "V1",
                    "file_name": "Summer Ad",
                    "duration": 15,
                    "width": 1080,
                    "height": 1920,
                    "poster_url": "https://example.com/cover.jpg",
                    "create_time": 1704067200,
                    "size": 5242880,
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_video_assets import get_video_assets

    result = asyncio.run(get_video_assets(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["video_id"] == "V1"
    assert result[0]["video_name"] == "Summer Ad"
    assert result[0]["duration"] == 15
    assert result[0]["width"] == 1080
    assert result[0]["height"] == 1920
    assert result[0]["cover_url"] == "https://example.com/cover.jpg"
    assert result[0]["create_time"] == 1704067200
    assert result[0]["size"] == 5242880
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"
    assert params["page"] == 1
    assert params["page_size"] == 20


def test_get_video_assets_passes_filtering():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"videos": []}}

    from tiktok_ads_mcp.tools.get_video_assets import get_video_assets

    asyncio.run(
        get_video_assets(
            mock_client,
            advertiser_id="111",
            filtering={"video_name": "Summer"},
            page=2,
            page_size=10,
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["filtering"] == json.dumps({"video_name": "Summer"})
    assert params["page"] == 2
    assert params["page_size"] == 10


# ---------------------------------------------------------------------------
# get_advertiser_balance
# ---------------------------------------------------------------------------

def test_get_advertiser_balance_returns_balance_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "advertiser_id": "111",
                    "balance": "1500.00",
                    "credit_limit": "5000.00",
                    "currency": "USD",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_advertiser_balance import get_advertiser_balance

    result = asyncio.run(get_advertiser_balance(mock_client, bc_id="BC1"))

    assert len(result) == 1
    assert result[0]["advertiser_id"] == "111"
    assert result[0]["balance"] == "1500.00"
    assert result[0]["credit_limit"] == "5000.00"
    assert result[0]["currency"] == "USD"
    params = mock_client._make_request.call_args[0][2]
    assert params["bc_id"] == "BC1"


def test_get_advertiser_balance_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_advertiser_balance import get_advertiser_balance

    result = asyncio.run(get_advertiser_balance(mock_client, bc_id="BC1"))
    assert result == []


# ---------------------------------------------------------------------------
# get_bc_assets
# ---------------------------------------------------------------------------

def test_get_bc_assets_returns_asset_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "asset_id": "A1",
                    "asset_name": "Main Account",
                    "asset_type": "ADVERTISER",
                    "status": "ENABLE",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_bc_assets import get_bc_assets

    result = asyncio.run(get_bc_assets(mock_client, bc_id="BC1", asset_type="ADVERTISER"))

    assert len(result) == 1
    assert result[0]["asset_id"] == "A1"
    assert result[0]["asset_name"] == "Main Account"
    assert result[0]["asset_type"] == "ADVERTISER"
    assert result[0]["status"] == "ENABLE"
    params = mock_client._make_request.call_args[0][2]
    assert params["bc_id"] == "BC1"
    assert params["asset_type"] == "ADVERTISER"


def test_get_bc_assets_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_bc_assets import get_bc_assets

    result = asyncio.run(get_bc_assets(mock_client, bc_id="BC1", asset_type="PIXEL"))
    assert result == []


# ---------------------------------------------------------------------------
# get_bc_members
# ---------------------------------------------------------------------------

def test_get_bc_members_returns_member_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "user_id": "U1",
                    "username": "jane_doe",
                    "email": "jane@example.com",
                    "role": "ADMIN",
                    "status": "ACTIVE",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_bc_members import get_bc_members

    result = asyncio.run(get_bc_members(mock_client, bc_id="BC1"))

    assert len(result) == 1
    assert result[0]["user_id"] == "U1"
    assert result[0]["username"] == "jane_doe"
    assert result[0]["email"] == "jane@example.com"
    assert result[0]["role"] == "ADMIN"
    assert result[0]["status"] == "ACTIVE"
    params = mock_client._make_request.call_args[0][2]
    assert params["bc_id"] == "BC1"


def test_get_bc_members_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_bc_members import get_bc_members

    result = asyncio.run(get_bc_members(mock_client, bc_id="BC1"))
    assert result == []
