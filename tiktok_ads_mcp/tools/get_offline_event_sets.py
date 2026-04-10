"""Get Offline Event Sets Tool"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_offline_event_sets(
    client,
    advertiser_id: str,
) -> List[Dict[str, Any]]:
    """List offline conversion event sets configured for an advertiser."""
    params: Dict[str, Any] = {"advertiser_id": advertiser_id}

    try:
        response = await client._make_request("GET", "/offline/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "event_set_id": item.get("event_set_id"),
                "name": item.get("name"),
                "status": item.get("status"),
                "event_types": item.get("event_types", []),
                "create_time": item.get("create_time"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get offline event sets: {e}")
        raise
