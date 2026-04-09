"""Get Audience Reach Tool"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_audience_reach(
    client,
    advertiser_id: str,
    objective_type: str,
    placements: Optional[List[str]] = None,
    age: Optional[List[str]] = None,
    gender: Optional[str] = None,
    location_ids: Optional[List[str]] = None,
    interest_category_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get estimated audience reach for given targeting criteria."""
    data: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "objective_type": objective_type,
    }
    if placements is not None:
        data["placements"] = placements
    if age is not None:
        data["age"] = age
    if gender is not None:
        data["gender"] = gender
    if location_ids is not None:
        data["location_ids"] = location_ids
    if interest_category_ids is not None:
        data["interest_category_ids"] = interest_category_ids

    try:
        response = await client._make_request("POST", "/tool/reach/forecast/", data=data)
        result = response.get("data", {})
        return {
            "estimated_audience_size_lower": result.get("lower"),
            "estimated_audience_size_upper": result.get("upper"),
            "reach_trend": result.get("reach_trend"),
        }
    except Exception as e:
        logger.error(f"Failed to get audience reach: {e}")
        raise
