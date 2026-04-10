"""Get Video Assets Tool"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_video_assets(
    client,
    advertiser_id: str,
    filtering: Optional[Dict] = None,
    page: int = 1,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """Browse the creative video asset library for an advertiser."""
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "page": page,
        "page_size": page_size,
    }
    if filtering:
        params["filtering"] = json.dumps(filtering)

    try:
        response = await client._make_request("GET", "/file/video/ad/search/", params)
        items = response.get("data", {}).get("videos", [])
        return [
            {
                "video_id": item.get("video_id"),
                "video_name": item.get("file_name"),
                "duration": item.get("duration"),
                "width": item.get("width"),
                "height": item.get("height"),
                "cover_url": item.get("poster_url"),
                "create_time": item.get("create_time"),
                "size": item.get("size"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get video assets: {e}")
        raise
