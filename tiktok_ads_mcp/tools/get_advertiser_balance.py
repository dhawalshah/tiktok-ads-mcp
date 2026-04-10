"""Get Advertiser Balance Tool"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_advertiser_balance(
    client,
    bc_id: str,
) -> List[Dict[str, Any]]:
    """Get balance details for all advertisers in a Business Center."""
    params: Dict[str, Any] = {"bc_id": bc_id}

    try:
        response = await client._make_request("GET", "/advertiser/balance/get/", params)
        items = response.get("data", {}).get("advertiser_account_list", [])
        return [
            {
                "advertiser_id": item.get("advertiser_id"),
                "advertiser_name": item.get("advertiser_name"),
                "balance": item.get("account_balance"),
                "cash_balance": item.get("cash_balance"),
                "currency": item.get("currency"),
                "timezone": item.get("timezone"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get advertiser balance: {e}")
        raise
