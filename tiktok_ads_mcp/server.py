#!/usr/bin/env python3
"""TikTok Ads MCP Server

A modern MCP server implementation for TikTok Business API integration using FastMCP.
This provides a clean, efficient interface to the TikTok Ads API with automatic schema generation.
"""

import json
import logging
import functools
from typing import Any, Dict, List, Optional

# MCP imports
from mcp.server import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# TikTok client
from .client import TikTokAdsClient
from .config import config
from .tools import (
    get_business_centers,
    get_authorized_ad_accounts,
    get_advertiser_info,
    get_campaigns,
    get_ad_groups,
    get_ads,
    get_reports,
    get_video_performance,
    get_creative_fatigue,
    get_ad_benchmark,
    create_async_report,
    check_async_report,
    download_async_report,
    get_audience_reach,
    get_targeting_options,
    get_pixels,
    get_smart_plus_campaigns,
    get_pixel_event_stats,
    get_video_assets,
    get_advertiser_balance,
    get_bc_assets,
    get_bc_members,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client instance (will be initialized on first use)
tiktok_client: Optional[TikTokAdsClient] = None

# Create MCP server instance
# Disable DNS rebinding protection — server runs behind HTTPS on Cloud Run,
# auth is handled by ApiKeyMiddleware in server_http.py.
app = FastMCP(
    "tiktok-ads",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

def get_tiktok_client() -> TikTokAdsClient:
    """Get or create TikTok API client instance"""
    global tiktok_client
    
    if tiktok_client is None:
        try:
            tiktok_client = TikTokAdsClient()
            logger.info("TikTok API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TikTok client: {e}")
            raise
    
    return tiktok_client

def handle_errors(func):
    """Decorator to handle errors in tool functions"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return json.dumps({
                "error": True,
                "message": f"Error: {str(e)}",
                "suggestion": "Please check your configuration and try again."
            }, indent=2)
    return wrapper

@app.tool()
@handle_errors
async def get_business_centers_tool(bc_id: str = "", page: int = 1, page_size: int = 10) -> str:
    """Get business centers accessible by the current access token"""
    client = get_tiktok_client()
    # Note: tools need to be updated to be async or we wrap them here if they are synchronous but use async client
    # Since we updated client to be async, the tools calling client._make_request must be awaited.
    # We will assume tools are updated to be async or return awaitables.
    centers = await get_business_centers(client, bc_id=bc_id, page=page, page_size=page_size)
    
    return json.dumps({
        "success": True,
        "count": len(centers),
        "centers": centers
    }, indent=2)

@app.tool()
@handle_errors
async def get_authorized_ad_accounts_tool(random_string: str = "") -> str:
    """Get all authorized ad accounts accessible by the current access token"""
    client = get_tiktok_client()
    advertisers = await get_authorized_ad_accounts(client)

    return json.dumps({
        "success": True,
        "count": len(advertisers),
        "advertisers": advertisers
    }, indent=2)

@app.tool()
@handle_errors
async def get_advertiser_info_tool(advertiser_ids: List[str]) -> str:
    """Get account-level metadata (currency, timezone, industry, status) for one or more advertisers.
    This is foundational context for interpreting all other data — especially date breakdowns,
    which depend on the account timezone."""
    if not advertiser_ids:
        raise ValueError("advertiser_ids is required")
    client = get_tiktok_client()
    advertisers = await get_advertiser_info(client, advertiser_ids=advertiser_ids)
    return json.dumps(
        {"success": True, "count": len(advertisers), "advertisers": advertisers},
        indent=2,
    )

@app.tool()
@handle_errors
async def get_campaigns_tool(advertiser_id: str, filters: Dict = None) -> str:
    """Get campaigns for a specific advertiser with optional filtering"""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    
    client = get_tiktok_client()
    campaigns = await get_campaigns(client, advertiser_id=advertiser_id, filters=filters or {})
    
    return json.dumps({
        "success": True,
        "advertiser_id": advertiser_id,
        "count": len(campaigns),
        "campaigns": campaigns
    }, indent=2)

@app.tool()
@handle_errors
async def get_ad_groups_tool(
    advertiser_id: str, 
    campaign_id: Optional[str] = None, 
    filters: Dict = None, 
    page: int = 1, 
    page_size: int = 10
) -> str:
    """Get ad groups for a specific advertiser with optional filtering"""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    
    client = get_tiktok_client()
    ad_groups = await get_ad_groups(client, advertiser_id=advertiser_id, campaign_id=campaign_id, filters=filters or {})
    
    return json.dumps({
        "success": True,
        "advertiser_id": advertiser_id,
        "campaign_id": campaign_id,
        "count": len(ad_groups),
        "ad_groups": ad_groups
    }, indent=2)

@app.tool()
@handle_errors
async def get_ads_tool(
    advertiser_id: str, 
    adgroup_id: Optional[str] = None, 
    filters: Dict = None, 
    page: int = 1, 
    page_size: int = 10
) -> str:
    """Get ads for a specific advertiser with optional filtering"""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    
    client = get_tiktok_client()
    ads = await get_ads(client, advertiser_id=advertiser_id, adgroup_id=adgroup_id, filters=filters or {})
    
    return json.dumps({
        "success": True,
        "advertiser_id": advertiser_id,
        "adgroup_id": adgroup_id,
        "count": len(ads),
        "ads": ads
    }, indent=2)

@app.tool()
@handle_errors
async def get_reports_tool(
    advertiser_id: Optional[str] = None,
    advertiser_ids: Optional[List[str]] = None,
    bc_id: Optional[str] = None,
    report_type: str = "BASIC",
    data_level: str = "AUCTION_CAMPAIGN",
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    filters: Optional[List[Dict]] = None,
    page: int = 1,
    page_size: int = 10,
    service_type: str = "AUCTION",
    query_lifetime: bool = False,
    enable_total_metrics: bool = False,
    multi_adv_report_in_utc_time: bool = False,
    order_field: Optional[str] = None,
    order_type: str = "DESC"
) -> str:
    """Get performance reports and analytics with comprehensive filtering and grouping options"""

    client = get_tiktok_client()
    reports = await get_reports(
        client,
        advertiser_id=advertiser_id,
        advertiser_ids=advertiser_ids,
        bc_id=bc_id,
        report_type=report_type,
        data_level=data_level,
        dimensions=dimensions or ["campaign_id", "stat_time_day"],
        metrics=metrics or ["spend", "impressions"],
        start_date=start_date,
        end_date=end_date,
        filters=filters,
        page=page,
        page_size=page_size,
        service_type=service_type,
        query_lifetime=query_lifetime,
        enable_total_metrics=enable_total_metrics,
        multi_adv_report_in_utc_time=multi_adv_report_in_utc_time,
        order_field=order_field,
        order_type=order_type
    )

    return json.dumps({
        "success": True,
        "report_type": report_type,
        "data_level": data_level,
        "total_metrics": reports.get("total_metrics"),
        "page_info": reports.get("page_info", {}),
        "count": len(reports.get("list", [])),
        "reports": reports.get("list", [])
    }, indent=2)

@app.tool()
@handle_errors
async def get_video_performance_tool(
    advertiser_id: str,
    data_level: str = "AUCTION_AD",
    campaign_ids: Optional[List[str]] = None,
    adgroup_ids: Optional[List[str]] = None,
    ad_ids: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 10,
) -> str:
    """Get TikTok-specific video engagement metrics not available in the standard integrated report:
    2-second views, 6-second views, completion rate, average watch time, and video play actions.
    At least one of campaign_ids, adgroup_ids, or ad_ids is required.
    data_level: AUCTION_AD | AUCTION_ADGROUP | AUCTION_CAMPAIGN. Dates are YYYY-MM-DD."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not campaign_ids and not adgroup_ids and not ad_ids:
        raise ValueError("At least one of campaign_ids, adgroup_ids, or ad_ids is required")
    client = get_tiktok_client()
    result = await get_video_performance(
        client,
        advertiser_id=advertiser_id,
        data_level=data_level,
        campaign_ids=campaign_ids,
        adgroup_ids=adgroup_ids,
        ad_ids=ad_ids,
        start_date=start_date,
        end_date=end_date,
        dimensions=dimensions,
        page=page,
        page_size=page_size,
    )
    return json.dumps(
        {
            "success": True,
            "advertiser_id": advertiser_id,
            "page_info": result.get("page_info", {}),
            "count": len(result.get("list", [])),
            "rows": result.get("list", []),
        },
        indent=2,
    )

@app.tool()
@handle_errors
async def get_creative_fatigue_tool(
    advertiser_id: str,
    ad_ids: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Get creative fatigue scores per ad. Indicates when an ad has been shown too frequently
    to the same audience and needs refreshing. Returns fatigue_status, fatigue_level, and
    recommendations per ad. Optionally filter by ad_ids."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    items = await get_creative_fatigue(
        client, advertiser_id=advertiser_id, ad_ids=ad_ids, page=page, page_size=page_size
    )
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(items), "ads": items},
        indent=2,
    )

@app.tool()
@handle_errors
async def get_ad_benchmark_tool(
    advertiser_id: str,
    ad_ids: List[str],
    dimensions: Optional[List[str]] = None,
    objective_type: Optional[str] = None,
) -> str:
    """Get benchmark metrics (CTR, CVR, CPM, CPC) for specific ads compared to industry averages.
    ad_ids is required. dimensions defaults to ['PLACEMENT'].
    Allowed dimension values: AD_CATEGORY, EXTERNAL_ACTION, LOCATION, PLACEMENT.
    objective_type example: 'CONVERSIONS'."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not ad_ids:
        raise ValueError("ad_ids is required")
    client = get_tiktok_client()
    benchmarks = await get_ad_benchmark(
        client,
        advertiser_id=advertiser_id,
        ad_ids=ad_ids,
        dimensions=dimensions,
        objective_type=objective_type,
    )
    return json.dumps({"success": True, "benchmarks": benchmarks}, indent=2)


@app.tool()
@handle_errors
async def create_async_report_tool(
    advertiser_id: str,
    report_type: str,
    data_level: str,
    dimensions: List[str],
    metrics: List[str],
    start_date: str,
    end_date: str,
) -> str:
    """Creates an async report task for large datasets or long date ranges.
    After calling this tool, **immediately use check_async_report_tool with the returned
    task_id to monitor progress. When status is COMPLETE, use download_async_report_tool
    to retrieve the data.** Inform the user that the report is being generated and you
    will check on it.
    report_type: BASIC | AUDIENCE. data_level: AUCTION_AD | AUCTION_ADGROUP | AUCTION_CAMPAIGN.
    Dates are YYYY-MM-DD."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not report_type:
        raise ValueError("report_type is required")
    if not data_level:
        raise ValueError("data_level is required")
    if not dimensions:
        raise ValueError("dimensions is required")
    if not metrics:
        raise ValueError("metrics is required")
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required")
    client = get_tiktok_client()
    result = await create_async_report(
        client,
        advertiser_id=advertiser_id,
        report_type=report_type,
        data_level=data_level,
        dimensions=dimensions,
        metrics=metrics,
        start_date=start_date,
        end_date=end_date,
    )
    return json.dumps({"success": True, **result}, indent=2)


@app.tool()
@handle_errors
async def check_async_report_tool(advertiser_id: str, task_id: str) -> str:
    """Checks the status of an async report task created by create_async_report_tool.
    Status will be PROCESSING, COMPLETE, or FAILED.
    **If PROCESSING, inform the user the report is still generating and check again shortly.
    When COMPLETE, call download_async_report_tool with the same task_id.**"""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not task_id:
        raise ValueError("task_id is required")
    client = get_tiktok_client()
    result = await check_async_report(client, advertiser_id=advertiser_id, task_id=task_id)
    return json.dumps({"success": True, **result}, indent=2)


@app.tool()
@handle_errors
async def download_async_report_tool(advertiser_id: str, task_id: str) -> str:
    """Downloads the completed data for an async report task.
    **Only call after check_async_report_tool returns status COMPLETE.**
    Returns the report rows."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not task_id:
        raise ValueError("task_id is required")
    client = get_tiktok_client()
    rows = await download_async_report(client, advertiser_id=advertiser_id, task_id=task_id)
    count = len(rows) if isinstance(rows, list) else None
    result: Dict[str, Any] = {"success": True, "task_id": task_id}
    if count is not None:
        result["count"] = count
    result["rows"] = rows
    return json.dumps(result, indent=2)


@app.tool()
@handle_errors
async def get_audience_reach_tool(
    advertiser_id: str,
    objective_type: str,
    placements: Optional[List[str]] = None,
    age: Optional[List[str]] = None,
    gender: Optional[str] = None,
    location_ids: Optional[List[str]] = None,
    interest_category_ids: Optional[List[str]] = None,
) -> str:
    """Get estimated audience reach for given targeting criteria.
    NOTE: This endpoint requires allowlist access from TikTok. Contact TikTok support if you
    receive a 404 error. objective_type examples: 'TRAFFIC', 'CONVERSIONS', 'APP_INSTALL'.
    gender: 'GENDER_MALE' | 'GENDER_FEMALE' | 'GENDER_UNLIMITED'.
    Returns estimated_audience_size_lower, estimated_audience_size_upper, reach_trend."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not objective_type:
        raise ValueError("objective_type is required")
    client = get_tiktok_client()
    result = await get_audience_reach(
        client,
        advertiser_id=advertiser_id,
        objective_type=objective_type,
        placements=placements,
        age=age,
        gender=gender,
        location_ids=location_ids,
        interest_category_ids=interest_category_ids,
    )
    return json.dumps({"success": True, **result}, indent=2)


@app.tool()
@handle_errors
async def get_targeting_options_tool(
    advertiser_id: str,
    objective_type: Optional[str] = None,
) -> str:
    """Get all available interest categories for audience targeting.
    Returns a list of interest categories with their IDs, names, levels, and sub-category IDs.
    Use the returned interest_category_id values when setting up ad group targeting.
    Optionally filter by objective_type (e.g. 'TRAFFIC', 'CONVERSIONS')."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    options = await get_targeting_options(
        client,
        advertiser_id=advertiser_id,
        objective_type=objective_type,
    )
    return json.dumps(
        {"success": True, "count": len(options), "categories": options},
        indent=2,
    )


@app.tool()
@handle_errors
async def get_pixels_tool(
    advertiser_id: str,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """List all TikTok Pixel installations for an advertiser. Shows which conversion events
    are being tracked and whether measurement is set up correctly.
    Returns pixel_id, pixel_name, pixel_code, status, create_time, and tracked events."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    pixels = await get_pixels(client, advertiser_id=advertiser_id, page=page, page_size=page_size)
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(pixels), "pixels": pixels},
        indent=2,
    )


@app.tool()
@handle_errors
async def get_smart_plus_campaigns_tool(
    advertiser_id: str,
    campaign_ids: Optional[List[str]] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> str:
    """Get Smart+ (AI-optimised) campaigns for an advertiser.
    Smart+ campaigns do NOT appear in get_campaigns_tool — accounts using Smart+ have a blind spot
    without this tool. Returns campaign_id, name, status, budget, objective_type, create/modify times.
    status filter examples: 'ENABLE', 'DISABLE', 'DELETE'."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    campaigns = await get_smart_plus_campaigns(
        client,
        advertiser_id=advertiser_id,
        campaign_ids=campaign_ids,
        status=status,
        page=page,
        page_size=page_size,
    )
    return json.dumps(
        {
            "success": True,
            "advertiser_id": advertiser_id,
            "count": len(campaigns),
            "campaigns": campaigns,
        },
        indent=2,
    )


@app.tool()
@handle_errors
async def get_pixel_event_stats_tool(
    advertiser_id: str,
    pixel_ids: List[str],
    start_date: str,
    end_date: str,
) -> str:
    """Get aggregated conversion event counts (Purchase, AddToCart, ViewContent, etc.)
    per pixel over a date range. Use after get_pixels_tool to get pixel_ids.
    Dates are YYYY-MM-DD. Returns one row per pixel per event type per day."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not pixel_ids:
        raise ValueError("pixel_ids is required")
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required")
    client = get_tiktok_client()
    items = await get_pixel_event_stats(
        client,
        advertiser_id=advertiser_id,
        pixel_ids=pixel_ids,
        start_date=start_date,
        end_date=end_date,
    )
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(items), "events": items},
        indent=2,
    )


@app.tool()
@handle_errors
async def get_video_assets_tool(
    advertiser_id: str,
    filtering: Dict = None,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Browse the creative video asset library for an advertiser.
    Returns video_id, video_name, duration, width, height, cover_url, create_time, size.
    Optional filtering dict supports keys like 'video_name' for name search."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    items = await get_video_assets(
        client,
        advertiser_id=advertiser_id,
        filtering=filtering,
        page=page,
        page_size=page_size,
    )
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(items), "videos": items},
        indent=2,
    )


@app.tool()
@handle_errors
async def get_advertiser_balance_tool(bc_id: str) -> str:
    """Get cash balance and credit limit for all advertiser accounts within a Business Center.
    Returns advertiser_id, balance, credit_limit, and currency for each account.
    Use get_business_centers_tool first to get bc_id."""
    if not bc_id:
        raise ValueError("bc_id is required")
    client = get_tiktok_client()
    items = await get_advertiser_balance(client, bc_id=bc_id)
    return json.dumps(
        {"success": True, "bc_id": bc_id, "count": len(items), "balances": items},
        indent=2,
    )


@app.tool()
@handle_errors
async def get_bc_assets_tool(bc_id: str, asset_type: str) -> str:
    """Get all assets of a given type within a Business Center.
    asset_type must be one of: ADVERTISER, PIXEL, CATALOG.
    Returns asset_id, asset_name, asset_type, status for each asset.
    Use get_business_centers_tool first to get bc_id."""
    if not bc_id:
        raise ValueError("bc_id is required")
    if not asset_type:
        raise ValueError("asset_type is required — use ADVERTISER, PIXEL, or CATALOG")
    client = get_tiktok_client()
    items = await get_bc_assets(client, bc_id=bc_id, asset_type=asset_type)
    return json.dumps(
        {"success": True, "bc_id": bc_id, "asset_type": asset_type, "count": len(items), "assets": items},
        indent=2,
    )


@app.tool()
@handle_errors
async def get_bc_members_tool(bc_id: str) -> str:
    """Get all members of a Business Center, their roles, and access status.
    Returns user_id, username, email, role, status for each member.
    Useful for access audits. Use get_business_centers_tool first to get bc_id."""
    if not bc_id:
        raise ValueError("bc_id is required")
    client = get_tiktok_client()
    items = await get_bc_members(client, bc_id=bc_id)
    return json.dumps(
        {"success": True, "bc_id": bc_id, "count": len(items), "members": items},
        indent=2,
    )


def main():
    """Main function to run the MCP server"""
    logger.info("Starting TikTok Ads MCP Server...")
    
    # Log configuration status
    try:
        if not config.validate_credentials():
            logger.warning("Missing credentials detected. Server will start but API calls will fail.")
            missing = config.get_missing_credentials()
            logger.warning(f"Missing: {', '.join(missing)}")
        else:
            logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Failed to check configuration: {e}")
    
    # Run the MCP server using stdio transport
    app.run(transport="stdio")

if __name__ == "__main__":
    main()