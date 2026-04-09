"""Get Targeting Options Tool — returns interest categories from TikTok."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_targeting_options(
    client,
    advertiser_id: str,
    objective_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get available interest categories for targeting.

    Returns a tree of interest categories (level 1 and sub-categories).
    Use interest_category_id values when building audience targeting.
    """
    params: Dict[str, Any] = {"advertiser_id": advertiser_id}
    if objective_type is not None:
        params["objective_type"] = objective_type

    try:
        response = await client._make_request("GET", "/tool/interest_category/", params)
        categories = response.get("data", {}).get("interest_categories", [])
        return [
            {
                "id": cat.get("interest_category_id"),
                "name": cat.get("interest_category_name"),
                "level": cat.get("level"),
                "sub_category_ids": cat.get("sub_category_ids", []),
            }
            for cat in categories
        ]
    except Exception as e:
        logger.error(f"Failed to get targeting options: {e}")
        raise
