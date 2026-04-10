"""Get Advertiser Balance Tool"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_advertiser_balance(
    client,
    bc_id: str,
) -> List[Dict[str, Any]]:
    """Get cash balance and credit limit for all advertisers in a Business Center."""
    params: Dict[str, Any] = {"bc_id": bc_id}

    try:
        response = await client._make_request("GET", "/advertiser/balance/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "advertiser_id": item.get("advertiser_id"),
                "balance": item.get("balance"),
                "credit_limit": item.get("credit_limit"),
                "currency": item.get("currency"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get advertiser balance: {e}")
        raise
