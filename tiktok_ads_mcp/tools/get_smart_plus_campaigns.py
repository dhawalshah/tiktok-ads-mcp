"""Get Smart+ Campaigns Tool"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_smart_plus_campaigns(
    client,
    advertiser_id: str,
    campaign_ids: Optional[List[str]] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> List[Dict[str, Any]]:
    """Get Smart+ (AI-optimised) campaigns — these do not appear in /campaign/get/."""
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "page": page,
        "page_size": page_size,
    }
    if campaign_ids is not None:
        params["campaign_ids"] = json.dumps(campaign_ids)
    if status is not None:
        params["status"] = status

    try:
        response = await client._make_request("GET", "/smart_plus/campaign/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "campaign_id": item.get("campaign_id"),
                "campaign_name": item.get("campaign_name"),
                "status": item.get("status"),
                "budget": item.get("budget"),
                "budget_mode": item.get("budget_mode"),
                "objective_type": item.get("objective_type"),
                "create_time": item.get("create_time"),
                "modify_time": item.get("modify_time"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get Smart+ campaigns: {e}")
        raise
