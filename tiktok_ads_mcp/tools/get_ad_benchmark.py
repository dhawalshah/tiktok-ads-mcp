"""Get Ad Benchmark Tool"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_ad_benchmark(
    client,
    advertiser_id: str,
    ad_ids: List[str],
    dimensions: Optional[List[str]] = None,
    objective_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Get industry benchmark metrics (CTR, CVR, CPM, CPC) compared against your ads.

    ad_ids is required. dimensions defaults to ['PLACEMENT'].
    Allowed dimension values: AD_CATEGORY, EXTERNAL_ACTION, LOCATION, PLACEMENT.
    """
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "dimensions": json.dumps(dimensions if dimensions is not None else ["PLACEMENT"]),
        "filtering": json.dumps({"ad_ids": ad_ids}),
    }
    if objective_type is not None:
        params["objective_type"] = objective_type

    try:
        response = await client._make_request("GET", "/report/ad_benchmark/get/", params)
        return response.get("data", {})
    except Exception as e:
        logger.error(f"Failed to get ad benchmark: {e}")
        raise
