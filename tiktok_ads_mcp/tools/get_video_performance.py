"""Get Video Performance Tool"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_video_performance(
    client,
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
) -> Dict[str, Any]:
    """Get TikTok-specific video engagement metrics per ad/adgroup/campaign.

    At least one of campaign_ids, adgroup_ids, or ad_ids is required by the API.
    """
    filtering: Dict[str, Any] = {}
    if campaign_ids is not None:
        filtering["campaign_ids"] = campaign_ids
    if adgroup_ids is not None:
        filtering["adgroup_ids"] = adgroup_ids
    if ad_ids is not None:
        filtering["ad_ids"] = ad_ids

    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "data_level": data_level,
        "filtering": json.dumps(filtering),
        "page": page,
        "page_size": page_size,
    }
    if dimensions is not None:
        params["dimensions"] = json.dumps(dimensions)
    if start_date is not None:
        params["start_date"] = start_date
    if end_date is not None:
        params["end_date"] = end_date

    try:
        response = await client._make_request("GET", "/report/video_performance/get/", params)
        data = response.get("data", {})
        return {
            "list": data.get("list", []),
            "page_info": data.get("page_info", {}),
        }
    except Exception as e:
        logger.error(f"Failed to get video performance: {e}")
        raise
