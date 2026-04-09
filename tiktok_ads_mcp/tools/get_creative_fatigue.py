"""Get Creative Fatigue Tool"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_creative_fatigue(
    client,
    advertiser_id: str,
    ad_ids: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """Get creative fatigue scores per ad — indicates when an ad needs refreshing."""
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "page": page,
        "page_size": page_size,
    }
    if ad_ids:
        params["ad_ids"] = json.dumps(ad_ids)

    try:
        response = await client._make_request("GET", "/creative_fatigue/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "ad_id": item.get("ad_id"),
                "ad_name": item.get("ad_name"),
                "fatigue_status": item.get("fatigue_status"),
                "fatigue_level": item.get("fatigue_level"),
                "recommendation": item.get("recommendation"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get creative fatigue: {e}")
        raise
