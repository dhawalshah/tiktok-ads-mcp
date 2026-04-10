"""Get BC Assets Tool"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_bc_assets(
    client,
    bc_id: str,
    asset_type: str,
) -> List[Dict[str, Any]]:
    """Get all assets of a given type within a Business Center."""
    params: Dict[str, Any] = {
        "bc_id": bc_id,
        "asset_type": asset_type,
    }

    try:
        response = await client._make_request("GET", "/bc/asset/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "asset_id": item.get("asset_id"),
                "asset_name": item.get("asset_name"),
                "asset_type": item.get("asset_type"),
                "status": item.get("status"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get BC assets: {e}")
        raise
