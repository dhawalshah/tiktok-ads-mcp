"""Async Report Workflow Tools — create / check / download"""

import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)


async def create_async_report(
    client,
    advertiser_id: str,
    report_type: str,
    data_level: str,
    dimensions: List[str],
    metrics: List[str],
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """Create an async report task. Returns task_id to use with check_async_report."""
    data = {
        "advertiser_id": advertiser_id,
        "report_type": report_type,
        "data_level": data_level,
        "dimensions": dimensions,
        "metrics": metrics,
        "start_date": start_date,
        "end_date": end_date,
    }
    try:
        response = await client._make_request("POST", "/report/task/create/", data=data)
        task_id = response.get("data", {}).get("task_id")
        return {"task_id": task_id, "status": "PROCESSING"}
    except Exception as e:
        logger.error(f"Failed to create async report: {e}")
        raise


async def check_async_report(
    client,
    advertiser_id: str,
    task_id: str,
) -> Dict[str, Any]:
    """Check the status of an async report task. Status: PROCESSING | COMPLETE | FAILED."""
    params = {"advertiser_id": advertiser_id, "task_id": task_id}
    try:
        response = await client._make_request("GET", "/report/task/check/", params)
        task_data = response.get("data", {})
        return {
            "task_id": task_data.get("task_id", task_id),
            "status": task_data.get("status"),
            "progress_rate": task_data.get("progress_rate"),
        }
    except Exception as e:
        logger.error(f"Failed to check async report: {e}")
        raise


async def download_async_report(
    client,
    advertiser_id: str,
    task_id: str,
) -> Any:
    """Download rows from a COMPLETE async report task.
    Handles both inline rows and download-URL responses."""
    params = {"advertiser_id": advertiser_id, "task_id": task_id}
    try:
        response = await client._make_request("GET", "/report/task/download/", params)
        data = response.get("data", {})

        # API may return a URL instead of inline data
        download_url = data.get("download_url") or data.get("url")
        if download_url:
            async with httpx.AsyncClient(timeout=60) as http_client:
                url_resp = await http_client.get(download_url)
                url_resp.raise_for_status()
                try:
                    return url_resp.json()
                except Exception:
                    return {"raw": url_resp.text}

        return data.get("list", data)
    except Exception as e:
        logger.error(f"Failed to download async report: {e}")
        raise
