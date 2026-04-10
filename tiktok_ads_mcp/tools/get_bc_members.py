"""Get BC Members Tool"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_bc_members(
    client,
    bc_id: str,
) -> List[Dict[str, Any]]:
    """Get all members of a Business Center and their roles."""
    params: Dict[str, Any] = {"bc_id": bc_id}

    try:
        response = await client._make_request("GET", "/bc/member/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "user_id": item.get("user_id"),
                "username": item.get("username"),
                "email": item.get("email"),
                "role": item.get("role"),
                "status": item.get("status"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get BC members: {e}")
        raise
