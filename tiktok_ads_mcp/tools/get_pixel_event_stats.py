"""Get Pixel Event Stats Tool"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_pixel_event_stats(
    client,
    advertiser_id: str,
    pixel_ids: List[str],
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """Get aggregated conversion event counts per pixel over a date range."""
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "pixel_ids": json.dumps(pixel_ids),
        "start_date": start_date,
        "end_date": end_date,
    }

    try:
        response = await client._make_request("GET", "/pixel/event/stats/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "pixel_id": item.get("pixel_id"),
                "event_type": item.get("event_type"),
                "date": item.get("date"),
                "count": item.get("count"),
                "match_rate": item.get("match_rate"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get pixel event stats: {e}")
        raise
