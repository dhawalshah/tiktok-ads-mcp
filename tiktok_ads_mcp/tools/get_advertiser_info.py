"""Get Advertiser Info Tool"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_advertiser_info(client, advertiser_ids: List[str]) -> List[Dict[str, Any]]:
    """Get account-level metadata for one or more advertisers."""
    params = {"advertiser_ids": json.dumps(advertiser_ids)}

    try:
        response = await client._make_request("GET", "/advertiser/info/", params)
        advertisers = response.get("data", {}).get("list", [])
        return [
            {
                "advertiser_id": adv.get("advertiser_id"),
                "name": adv.get("name"),
                "currency": adv.get("currency"),
                "timezone": adv.get("timezone"),
                "industry": adv.get("industry"),
                "status": adv.get("status"),
                "description": adv.get("description"),
                "phone_number": adv.get("phone_number"),
                "address": adv.get("address"),
                "contacter": adv.get("contacter"),
            }
            for adv in advertisers
        ]
    except Exception as e:
        logger.error(f"Failed to get advertiser info: {e}")
        raise
