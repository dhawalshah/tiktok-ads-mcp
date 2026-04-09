"""Get Ad Benchmark Tool"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def get_ad_benchmark(
    client,
    advertiser_id: str,
    industry_id: Optional[str] = None,
    placement_type: Optional[str] = None,
    objective_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Get industry benchmark metrics (CTR, CVR, CPM, CPC) by vertical and placement."""
    params: Dict[str, Any] = {"advertiser_id": advertiser_id}
    if industry_id:
        params["industry_id"] = industry_id
    if placement_type:
        params["placement_type"] = placement_type
    if objective_type:
        params["objective_type"] = objective_type

    try:
        response = await client._make_request("GET", "/report/ad_benchmark/get/", params)
        return response.get("data", {})
    except Exception as e:
        logger.error(f"Failed to get ad benchmark: {e}")
        raise
