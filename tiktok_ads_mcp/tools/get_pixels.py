"""Get Pixels Tool"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_pixels(
    client,
    advertiser_id: str,
    page: int = 1,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """List all TikTok Pixel installations for an advertiser."""
    params = {"advertiser_id": advertiser_id, "page": page, "page_size": page_size}

    try:
        response = await client._make_request("GET", "/pixel/list/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "pixel_id": item.get("pixel_id"),
                "pixel_name": item.get("pixel_name"),
                "pixel_code": item.get("pixel_code"),
                "status": item.get("status"),
                "create_time": item.get("create_time"),
                "events": item.get("events", []),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get pixels: {e}")
        raise
