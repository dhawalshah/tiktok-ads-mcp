"""Get Targeting Options Tool"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_targeting_options(
    client,
    advertiser_id: str,
    query: str,
    objective_type: Optional[str] = None,
    targeting_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search available targeting options (interests, behaviors) by keyword."""
    params: Dict[str, Any] = {"advertiser_id": advertiser_id, "query": query}
    if objective_type is not None:
        params["objective_type"] = objective_type
    if targeting_type is not None:
        params["targeting_type"] = targeting_type

    try:
        response = await client._make_request("GET", "/tool/targeting/search/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "type": item.get("type"),
                "audience_size": item.get("audience_size"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get targeting options: {e}")
        raise
