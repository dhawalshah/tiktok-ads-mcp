# New Tools Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 12 new read-only MCP tools covering TikTok's approved API scopes — advertiser info, video performance, creative fatigue, ad benchmarks, async reporting, audience reach, targeting options, pixels, and Smart+ campaigns.

**Architecture:** Each tool lives in its own file under `tiktok_ads_mcp/tools/`, exporting a pure async function that takes `client` + params and returns a list or dict. `server.py` adds a `@app.tool()` wrapper that validates required params, calls the tool function, and returns a `{success, ...}` JSON envelope. `tools/__init__.py` gains one import per new file.

**Tech Stack:** Python 3.10, FastMCP (`mcp>=1.9.0`), httpx (for download URL following in async reports), pytest + unittest.mock for tests.

---

## File Map

**New files (one per tool module):**
- `tiktok_ads_mcp/tools/get_advertiser_info.py`
- `tiktok_ads_mcp/tools/get_video_performance.py`
- `tiktok_ads_mcp/tools/get_creative_fatigue.py`
- `tiktok_ads_mcp/tools/get_ad_benchmark.py`
- `tiktok_ads_mcp/tools/async_reports.py` (3 functions: create / check / download)
- `tiktok_ads_mcp/tools/get_audience_reach.py`
- `tiktok_ads_mcp/tools/get_targeting_options.py`
- `tiktok_ads_mcp/tools/get_pixels.py`
- `tiktok_ads_mcp/tools/get_smart_plus_campaigns.py`
- `tests/test_new_tools.py` (all tool-function unit tests in one file)

**Modified files:**
- `tiktok_ads_mcp/tools/__init__.py` — add 12 imports (one per task)
- `tiktok_ads_mcp/server.py` — add 12 `@app.tool()` wrappers (one per task)

---

## Reference: Existing patterns

**Tool file pattern** (see `tiktok_ads_mcp/tools/get_campaigns.py`):
```python
async def my_tool(client, required_param: str, optional_param: str = "default") -> List[Dict]:
    params = {"required_param": required_param}
    response = await client._make_request("GET", "/endpoint/path/", params)
    items = response.get("data", {}).get("list", [])
    return [{"field": item.get("field")} for item in items]
```

**Server wrapper pattern** (see `tiktok_ads_mcp/server.py`):
```python
@app.tool()
@handle_errors
async def my_tool_tool(required_param: str, optional_param: str = "default") -> str:
    """Tool description shown to Claude."""
    if not required_param:
        raise ValueError("required_param is required")
    client = get_tiktok_client()
    result = await my_tool(client, required_param=required_param, optional_param=optional_param)
    return json.dumps({"success": True, "count": len(result), "items": result}, indent=2)
```

**Test pattern** (see `tests/test_server_http.py`):
```python
import asyncio
from unittest.mock import AsyncMock

def test_something():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": [...]}}
    from tiktok_ads_mcp.tools.my_tool import my_tool
    result = asyncio.run(my_tool(mock_client, required_param="123"))
    assert result[0]["field"] == "expected"
```

**POST requests:** Pass body as `data=` kwarg, no `params`. The client puts `params` in the query string and `data` in the JSON body.

---

## Task 1: `get_advertiser_info`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_advertiser_info.py`
- Create: `tests/test_new_tools.py`
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_new_tools.py`:

```python
"""Unit tests for new TikTok Ads MCP tools (Tasks 1–9).

Each test mocks client._make_request and calls the tool function directly.
Uses asyncio.run() — no pytest-asyncio needed.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Task 1: get_advertiser_info
# ---------------------------------------------------------------------------

def test_get_advertiser_info_returns_advertisers():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "advertiser_id": "111",
                    "name": "Test Co",
                    "currency": "USD",
                    "timezone": "America/New_York",
                    "industry": "ECOMMERCE",
                    "status": "STATUS_ENABLE",
                    "description": "desc",
                    "phone_number": "555",
                    "address": "addr",
                    "contacter": "Jane",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_advertiser_info import get_advertiser_info

    result = asyncio.run(get_advertiser_info(mock_client, advertiser_ids=["111"]))

    assert len(result) == 1
    assert result[0]["advertiser_id"] == "111"
    assert result[0]["currency"] == "USD"
    assert result[0]["timezone"] == "America/New_York"
    mock_client._make_request.assert_called_once_with(
        "GET", "/advertiser/info/", {"advertiser_ids": json.dumps(["111"])}
    )


def test_get_advertiser_info_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_advertiser_info import get_advertiser_info

    result = asyncio.run(get_advertiser_info(mock_client, advertiser_ids=[]))
    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/dhawal/src/tiktok-ads-mcp
pytest tests/test_new_tools.py::test_get_advertiser_info_returns_advertisers -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `get_advertiser_info` does not exist yet.

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/get_advertiser_info.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_advertiser_info_returns_advertisers tests/test_new_tools.py::test_get_advertiser_info_empty_response -v
```

Expected: `2 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

In `tiktok_ads_mcp/tools/__init__.py`, add to the imports and `__all__`:

```python
from .get_advertiser_info import get_advertiser_info
```

Add `"get_advertiser_info"` to `__all__`.

- [ ] **Step 6: Add server wrapper to `server.py`**

In `tiktok_ads_mcp/server.py`, add `get_advertiser_info` to the `from .tools import (...)` block, then add this function after the existing tool wrappers:

```python
@app.tool()
@handle_errors
async def get_advertiser_info_tool(advertiser_ids: List[str]) -> str:
    """Get account-level metadata (currency, timezone, industry, status) for one or more advertisers.
    This is foundational context for interpreting all other data — especially date breakdowns,
    which depend on the account timezone."""
    if not advertiser_ids:
        raise ValueError("advertiser_ids is required")
    client = get_tiktok_client()
    advertisers = await get_advertiser_info(client, advertiser_ids=advertiser_ids)
    return json.dumps(
        {"success": True, "count": len(advertisers), "advertisers": advertisers},
        indent=2,
    )
```

- [ ] **Step 7: Run full test suite to confirm no regressions**

```bash
pytest tests/ -v
```

Expected: all previously passing tests still pass, plus 2 new ones.

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/get_advertiser_info.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_advertiser_info tool (advertiser account metadata)"
```

---

## Task 2: `get_video_performance`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_video_performance.py`
- Modify: `tests/test_new_tools.py` (append tests)
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Append failing tests to `tests/test_new_tools.py`**

```python
# ---------------------------------------------------------------------------
# Task 2: get_video_performance
# ---------------------------------------------------------------------------

def test_get_video_performance_returns_rows_and_page_info():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [{"dimensions": {"ad_id": "A1"}, "metrics": {"play_over_6s": "500"}}],
            "page_info": {"total_number": 1, "page": 1, "page_size": 10},
        },
    }

    from tiktok_ads_mcp.tools.get_video_performance import get_video_performance

    result = asyncio.run(
        get_video_performance(mock_client, advertiser_id="111", start_date="2024-01-01", end_date="2024-01-31")
    )

    assert len(result["list"]) == 1
    assert result["list"][0]["dimensions"]["ad_id"] == "A1"
    assert "page_info" in result
    mock_client._make_request.assert_called_once()
    call_args = mock_client._make_request.call_args
    assert call_args[0][0] == "GET"
    assert call_args[0][1] == "/report/video_performance/get/"
    assert call_args[0][2]["advertiser_id"] == "111"


def test_get_video_performance_dimensions_json_encoded():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": [], "page_info": {}}}

    from tiktok_ads_mcp.tools.get_video_performance import get_video_performance

    asyncio.run(
        get_video_performance(
            mock_client,
            advertiser_id="111",
            dimensions=["ad_id", "stat_time_day"],
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["dimensions"] == json.dumps(["ad_id", "stat_time_day"])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_video_performance_returns_rows_and_page_info -v
```

Expected: `ImportError` — module does not exist yet.

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/get_video_performance.py`:

```python
"""Get Video Performance Tool"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_video_performance(
    client,
    advertiser_id: str,
    data_level: str = "AUCTION_AD",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 10,
) -> Dict[str, Any]:
    """Get TikTok-specific video engagement metrics per ad/adgroup/campaign."""
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "data_level": data_level,
        "page": page,
        "page_size": page_size,
    }
    if dimensions:
        params["dimensions"] = json.dumps(dimensions)
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    try:
        response = await client._make_request("GET", "/report/video_performance/get/", params)
        data = response.get("data", {})
        return {
            "list": data.get("list", []),
            "page_info": data.get("page_info", {}),
        }
    except Exception as e:
        logger.error(f"Failed to get video performance: {e}")
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_video_performance_returns_rows_and_page_info tests/test_new_tools.py::test_get_video_performance_dimensions_json_encoded -v
```

Expected: `2 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

Add to imports and `__all__`:
```python
from .get_video_performance import get_video_performance
```

- [ ] **Step 6: Add server wrapper to `server.py`**

Add `get_video_performance` to the import block, then add:

```python
@app.tool()
@handle_errors
async def get_video_performance_tool(
    advertiser_id: str,
    data_level: str = "AUCTION_AD",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 10,
) -> str:
    """Get TikTok-specific video engagement metrics not available in the standard integrated report:
    2-second views, 6-second views, completion rate, average watch time, and video play actions.
    data_level: AUCTION_AD | AUCTION_ADGROUP | AUCTION_CAMPAIGN. Dates are YYYY-MM-DD."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    result = await get_video_performance(
        client,
        advertiser_id=advertiser_id,
        data_level=data_level,
        start_date=start_date,
        end_date=end_date,
        dimensions=dimensions,
        page=page,
        page_size=page_size,
    )
    return json.dumps(
        {
            "success": True,
            "advertiser_id": advertiser_id,
            "page_info": result["page_info"],
            "count": len(result["list"]),
            "rows": result["list"],
        },
        indent=2,
    )
```

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/get_video_performance.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_video_performance tool (TikTok video engagement metrics)"
```

---

## Task 3: `get_creative_fatigue`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_creative_fatigue.py`
- Modify: `tests/test_new_tools.py` (append tests)
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Append failing tests**

```python
# ---------------------------------------------------------------------------
# Task 3: get_creative_fatigue
# ---------------------------------------------------------------------------

def test_get_creative_fatigue_returns_fatigue_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "ad_id": "AD1",
                    "ad_name": "Summer Sale",
                    "fatigue_status": "HIGH",
                    "fatigue_level": 85,
                    "recommendation": "Refresh creative",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_creative_fatigue import get_creative_fatigue

    result = asyncio.run(get_creative_fatigue(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["ad_id"] == "AD1"
    assert result[0]["fatigue_status"] == "HIGH"
    assert result[0]["recommendation"] == "Refresh creative"


def test_get_creative_fatigue_passes_ad_ids():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_creative_fatigue import get_creative_fatigue

    asyncio.run(get_creative_fatigue(mock_client, advertiser_id="111", ad_ids=["AD1", "AD2"]))

    params = mock_client._make_request.call_args[0][2]
    assert params["ad_ids"] == json.dumps(["AD1", "AD2"])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_creative_fatigue_returns_fatigue_list -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/get_creative_fatigue.py`:

```python
"""Get Creative Fatigue Tool"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_creative_fatigue(
    client,
    advertiser_id: str,
    ad_ids: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """Get creative fatigue scores per ad — indicates when an ad needs refreshing."""
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "page": page,
        "page_size": page_size,
    }
    if ad_ids:
        params["ad_ids"] = json.dumps(ad_ids)

    try:
        response = await client._make_request("GET", "/creative_fatigue/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "ad_id": item.get("ad_id"),
                "ad_name": item.get("ad_name"),
                "fatigue_status": item.get("fatigue_status"),
                "fatigue_level": item.get("fatigue_level"),
                "recommendation": item.get("recommendation"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get creative fatigue: {e}")
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_creative_fatigue_returns_fatigue_list tests/test_new_tools.py::test_get_creative_fatigue_passes_ad_ids -v
```

Expected: `2 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

```python
from .get_creative_fatigue import get_creative_fatigue
```

- [ ] **Step 6: Add server wrapper to `server.py`**

Add `get_creative_fatigue` to the import block, then add:

```python
@app.tool()
@handle_errors
async def get_creative_fatigue_tool(
    advertiser_id: str,
    ad_ids: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Get creative fatigue scores per ad. Indicates when an ad has been shown too frequently
    to the same audience and needs refreshing. Returns fatigue_status, fatigue_level, and
    recommendations per ad. Optionally filter by ad_ids."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    items = await get_creative_fatigue(
        client, advertiser_id=advertiser_id, ad_ids=ad_ids, page=page, page_size=page_size
    )
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(items), "ads": items},
        indent=2,
    )
```

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/get_creative_fatigue.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_creative_fatigue tool (ad fatigue scores and recommendations)"
```

---

## Task 4: `get_ad_benchmark`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_ad_benchmark.py`
- Modify: `tests/test_new_tools.py`
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Append failing tests**

```python
# ---------------------------------------------------------------------------
# Task 4: get_ad_benchmark
# ---------------------------------------------------------------------------

def test_get_ad_benchmark_returns_benchmark_dict():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "industry": "ECOMMERCE",
            "placement": "PLACEMENT_TIKTOK",
            "ctr": "1.5",
            "cpm": "8.0",
            "cpc": "0.53",
            "cvr": "2.1",
        },
    }

    from tiktok_ads_mcp.tools.get_ad_benchmark import get_ad_benchmark

    result = asyncio.run(get_ad_benchmark(mock_client, advertiser_id="111"))

    assert result["ctr"] == "1.5"
    assert result["industry"] == "ECOMMERCE"


def test_get_ad_benchmark_passes_optional_filters():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {}}

    from tiktok_ads_mcp.tools.get_ad_benchmark import get_ad_benchmark

    asyncio.run(
        get_ad_benchmark(
            mock_client,
            advertiser_id="111",
            industry_id="IND_001",
            placement_type="PLACEMENT_TIKTOK",
            objective_type="CONVERSIONS",
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["industry_id"] == "IND_001"
    assert params["placement_type"] == "PLACEMENT_TIKTOK"
    assert params["objective_type"] == "CONVERSIONS"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_ad_benchmark_returns_benchmark_dict -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/get_ad_benchmark.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_ad_benchmark_returns_benchmark_dict tests/test_new_tools.py::test_get_ad_benchmark_passes_optional_filters -v
```

Expected: `2 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

```python
from .get_ad_benchmark import get_ad_benchmark
```

- [ ] **Step 6: Add server wrapper to `server.py`**

Add `get_ad_benchmark` to the import block, then add:

```python
@app.tool()
@handle_errors
async def get_ad_benchmark_tool(
    advertiser_id: str,
    industry_id: Optional[str] = None,
    placement_type: Optional[str] = None,
    objective_type: Optional[str] = None,
) -> str:
    """Get industry benchmark metrics (CTR, CVR, CPM, CPC) by vertical and placement.
    Use to evaluate whether account performance is above or below industry average.
    placement_type example: 'PLACEMENT_TIKTOK'. objective_type example: 'CONVERSIONS'."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    benchmarks = await get_ad_benchmark(
        client,
        advertiser_id=advertiser_id,
        industry_id=industry_id,
        placement_type=placement_type,
        objective_type=objective_type,
    )
    return json.dumps({"success": True, "benchmarks": benchmarks}, indent=2)
```

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/get_ad_benchmark.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_ad_benchmark tool (industry benchmark metrics)"
```

---

## Task 5: Async Report Workflow (3 tools)

**Files:**
- Create: `tiktok_ads_mcp/tools/async_reports.py`
- Modify: `tests/test_new_tools.py`
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Append failing tests**

```python
# ---------------------------------------------------------------------------
# Task 5: async_reports (create / check / download)
# ---------------------------------------------------------------------------

def test_create_async_report_returns_task_id():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {"task_id": "TASK_001"},
    }

    from tiktok_ads_mcp.tools.async_reports import create_async_report

    result = asyncio.run(
        create_async_report(
            mock_client,
            advertiser_id="111",
            report_type="BASIC",
            data_level="AUCTION_AD",
            dimensions=["ad_id", "stat_time_day"],
            metrics=["spend", "impressions"],
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    )

    assert result["task_id"] == "TASK_001"
    assert result["status"] == "PROCESSING"
    # Verify it used POST with data body
    call_args = mock_client._make_request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "/report/task/create/"
    body = call_args[1]["data"]
    assert body["advertiser_id"] == "111"
    assert body["metrics"] == ["spend", "impressions"]


def test_check_async_report_returns_status():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {"task_id": "TASK_001", "status": "COMPLETE", "progress_rate": 100},
    }

    from tiktok_ads_mcp.tools.async_reports import check_async_report

    result = asyncio.run(check_async_report(mock_client, advertiser_id="111", task_id="TASK_001"))

    assert result["task_id"] == "TASK_001"
    assert result["status"] == "COMPLETE"
    assert result["progress_rate"] == 100
    call_args = mock_client._make_request.call_args[0]
    assert call_args[0] == "GET"
    assert call_args[2]["task_id"] == "TASK_001"


def test_download_async_report_inline_rows():
    """When API returns rows directly (no URL), return them."""
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {"list": [{"dimensions": {}, "metrics": {"spend": "100"}}]},
    }

    from tiktok_ads_mcp.tools.async_reports import download_async_report

    result = asyncio.run(download_async_report(mock_client, advertiser_id="111", task_id="TASK_001"))

    assert result == [{"dimensions": {}, "metrics": {"spend": "100"}}]


def test_download_async_report_follows_download_url():
    """When API returns a download_url, fetch it and return JSON rows."""
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {"download_url": "https://example.com/report.json"},
    }

    mock_http_response = MagicMock()
    mock_http_response.raise_for_status = MagicMock()
    mock_http_response.json.return_value = [{"row": 1}]
    mock_http_response.text = '[{"row": 1}]'

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_http_response

    with patch("tiktok_ads_mcp.tools.async_reports.httpx.AsyncClient") as MockClass:
        MockClass.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
        MockClass.return_value.__aexit__ = AsyncMock(return_value=None)

        from tiktok_ads_mcp.tools.async_reports import download_async_report

        result = asyncio.run(download_async_report(mock_client, advertiser_id="111", task_id="TASK_001"))

    assert result == [{"row": 1}]
    mock_http_client.get.assert_called_once_with("https://example.com/report.json")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_create_async_report_returns_task_id -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/async_reports.py`:

```python
"""Async Report Workflow Tools — create / check / download"""

import logging
from typing import Any, Dict, List, Optional

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_create_async_report_returns_task_id tests/test_new_tools.py::test_check_async_report_returns_status tests/test_new_tools.py::test_download_async_report_inline_rows tests/test_new_tools.py::test_download_async_report_follows_download_url -v
```

Expected: `4 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

```python
from .async_reports import create_async_report, check_async_report, download_async_report
```

Add all three to `__all__`.

- [ ] **Step 6: Add server wrappers to `server.py`**

Add `create_async_report`, `check_async_report`, `download_async_report` to the import block, then add these three functions:

```python
@app.tool()
@handle_errors
async def create_async_report_tool(
    advertiser_id: str,
    report_type: str,
    data_level: str,
    dimensions: List[str],
    metrics: List[str],
    start_date: str,
    end_date: str,
) -> str:
    """Creates an async report task for large datasets or long date ranges.
    After calling this tool, **immediately use check_async_report_tool with the returned
    task_id to monitor progress. When status is COMPLETE, use download_async_report_tool
    to retrieve the data.** Inform the user that the report is being generated and you
    will check on it.
    report_type: BASIC | AUDIENCE. data_level: AUCTION_AD | AUCTION_ADGROUP | AUCTION_CAMPAIGN.
    Dates are YYYY-MM-DD."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not dimensions:
        raise ValueError("dimensions is required")
    if not metrics:
        raise ValueError("metrics is required")
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required")
    client = get_tiktok_client()
    result = await create_async_report(
        client,
        advertiser_id=advertiser_id,
        report_type=report_type,
        data_level=data_level,
        dimensions=dimensions,
        metrics=metrics,
        start_date=start_date,
        end_date=end_date,
    )
    return json.dumps({"success": True, **result}, indent=2)


@app.tool()
@handle_errors
async def check_async_report_tool(advertiser_id: str, task_id: str) -> str:
    """Checks the status of an async report task created by create_async_report_tool.
    Status will be PROCESSING, COMPLETE, or FAILED.
    **If PROCESSING, inform the user the report is still generating and check again shortly.
    When COMPLETE, call download_async_report_tool with the same task_id.**"""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not task_id:
        raise ValueError("task_id is required")
    client = get_tiktok_client()
    result = await check_async_report(client, advertiser_id=advertiser_id, task_id=task_id)
    return json.dumps({"success": True, **result}, indent=2)


@app.tool()
@handle_errors
async def download_async_report_tool(advertiser_id: str, task_id: str) -> str:
    """Downloads the completed data for an async report task.
    **Only call after check_async_report_tool returns status COMPLETE.**
    Returns the report rows."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not task_id:
        raise ValueError("task_id is required")
    client = get_tiktok_client()
    rows = await download_async_report(client, advertiser_id=advertiser_id, task_id=task_id)
    count = len(rows) if isinstance(rows, list) else None
    result: Dict[str, Any] = {"success": True, "task_id": task_id}
    if count is not None:
        result["count"] = count
    result["rows"] = rows
    return json.dumps(result, indent=2)
```

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/async_reports.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add async report workflow tools (create/check/download)"
```

---

## Task 6: `get_audience_reach`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_audience_reach.py`
- Modify: `tests/test_new_tools.py`
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Append failing tests**

```python
# ---------------------------------------------------------------------------
# Task 6: get_audience_reach
# ---------------------------------------------------------------------------

def test_get_audience_reach_returns_size_estimate():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "lower": 500000,
            "upper": 1200000,
            "reach_trend": [{"date": "2024-01-01", "reach": 600000}],
        },
    }

    from tiktok_ads_mcp.tools.get_audience_reach import get_audience_reach

    result = asyncio.run(
        get_audience_reach(
            mock_client,
            advertiser_id="111",
            objective_type="TRAFFIC",
            location_ids=["US"],
        )
    )

    assert result["estimated_audience_size_lower"] == 500000
    assert result["estimated_audience_size_upper"] == 1200000
    assert "reach_trend" in result
    # Verify POST with body containing advertiser_id and objective_type
    call_args = mock_client._make_request.call_args
    assert call_args[0][0] == "POST"
    body = call_args[1]["data"]
    assert body["advertiser_id"] == "111"
    assert body["objective_type"] == "TRAFFIC"
    assert body["location_ids"] == ["US"]


def test_get_audience_reach_omits_none_targeting():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {}}

    from tiktok_ads_mcp.tools.get_audience_reach import get_audience_reach

    asyncio.run(get_audience_reach(mock_client, advertiser_id="111", objective_type="TRAFFIC"))

    body = mock_client._make_request.call_args[1]["data"]
    assert "age" not in body
    assert "gender" not in body
    assert "placements" not in body
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_audience_reach_returns_size_estimate -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/get_audience_reach.py`:

```python
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
    if placements:
        data["placements"] = placements
    if age:
        data["age"] = age
    if gender:
        data["gender"] = gender
    if location_ids:
        data["location_ids"] = location_ids
    if interest_category_ids:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_audience_reach_returns_size_estimate tests/test_new_tools.py::test_get_audience_reach_omits_none_targeting -v
```

Expected: `2 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

```python
from .get_audience_reach import get_audience_reach
```

- [ ] **Step 6: Add server wrapper to `server.py`**

Add `get_audience_reach` to the import block, then add:

```python
@app.tool()
@handle_errors
async def get_audience_reach_tool(
    advertiser_id: str,
    objective_type: str,
    placements: Optional[List[str]] = None,
    age: Optional[List[str]] = None,
    gender: Optional[str] = None,
    location_ids: Optional[List[str]] = None,
    interest_category_ids: Optional[List[str]] = None,
) -> str:
    """Get estimated audience reach for given targeting criteria.
    Useful for planning campaigns and understanding audience size before launch.
    objective_type examples: 'TRAFFIC', 'CONVERSIONS', 'APP_INSTALL'.
    gender: 'GENDER_MALE' | 'GENDER_FEMALE' | 'GENDER_UNLIMITED'.
    Returns estimated_audience_size_lower, estimated_audience_size_upper, reach_trend."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not objective_type:
        raise ValueError("objective_type is required")
    client = get_tiktok_client()
    result = await get_audience_reach(
        client,
        advertiser_id=advertiser_id,
        objective_type=objective_type,
        placements=placements,
        age=age,
        gender=gender,
        location_ids=location_ids,
        interest_category_ids=interest_category_ids,
    )
    return json.dumps({"success": True, **result}, indent=2)
```

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/get_audience_reach.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_audience_reach tool (estimated audience size for targeting)"
```

---

## Task 7: `get_targeting_options`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_targeting_options.py`
- Modify: `tests/test_new_tools.py`
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Append failing tests**

```python
# ---------------------------------------------------------------------------
# Task 7: get_targeting_options
# ---------------------------------------------------------------------------

def test_get_targeting_options_returns_options_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "id": "INT_001",
                    "name": "Fitness & Wellness",
                    "type": "INTEREST",
                    "audience_size": 5000000,
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_targeting_options import get_targeting_options

    result = asyncio.run(
        get_targeting_options(mock_client, advertiser_id="111", query="fitness")
    )

    assert len(result) == 1
    assert result[0]["id"] == "INT_001"
    assert result[0]["type"] == "INTEREST"
    params = mock_client._make_request.call_args[0][2]
    assert params["query"] == "fitness"
    assert params["advertiser_id"] == "111"


def test_get_targeting_options_passes_optional_filters():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_targeting_options import get_targeting_options

    asyncio.run(
        get_targeting_options(
            mock_client,
            advertiser_id="111",
            query="sports",
            targeting_type="INTEREST",
            objective_type="TRAFFIC",
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["targeting_type"] == "INTEREST"
    assert params["objective_type"] == "TRAFFIC"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_targeting_options_returns_options_list -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/get_targeting_options.py`:

```python
"""Get Targeting Options Tool"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_targeting_options(
    client,
    advertiser_id: str,
    query: str,
    objective_type: Optional[str] = None,
    targeting_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search available targeting options (interests, behaviors) by keyword."""
    params: Dict[str, Any] = {"advertiser_id": advertiser_id, "query": query}
    if objective_type:
        params["objective_type"] = objective_type
    if targeting_type:
        params["targeting_type"] = targeting_type

    try:
        response = await client._make_request("GET", "/tool/targeting/search/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "type": item.get("type"),
                "audience_size": item.get("audience_size"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get targeting options: {e}")
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_targeting_options_returns_options_list tests/test_new_tools.py::test_get_targeting_options_passes_optional_filters -v
```

Expected: `2 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

```python
from .get_targeting_options import get_targeting_options
```

- [ ] **Step 6: Add server wrapper to `server.py`**

Add `get_targeting_options` to the import block, then add:

```python
@app.tool()
@handle_errors
async def get_targeting_options_tool(
    advertiser_id: str,
    query: str,
    objective_type: Optional[str] = None,
    targeting_type: Optional[str] = None,
) -> str:
    """Search available targeting options (interests, behaviors, demographics) by keyword.
    Use to answer questions like 'what TikTok interest categories exist for fitness brands?'
    targeting_type: 'INTEREST' | 'BEHAVIOR' | 'HASHTAG'. Returns id, name, type, audience_size."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not query:
        raise ValueError("query is required")
    client = get_tiktok_client()
    options = await get_targeting_options(
        client,
        advertiser_id=advertiser_id,
        query=query,
        objective_type=objective_type,
        targeting_type=targeting_type,
    )
    return json.dumps(
        {"success": True, "query": query, "count": len(options), "options": options},
        indent=2,
    )
```

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/get_targeting_options.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_targeting_options tool (search interest/behavior categories)"
```

---

## Task 8: `get_pixels`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_pixels.py`
- Modify: `tests/test_new_tools.py`
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Append failing tests**

```python
# ---------------------------------------------------------------------------
# Task 8: get_pixels
# ---------------------------------------------------------------------------

def test_get_pixels_returns_pixel_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "pixel_id": "PX1",
                    "pixel_name": "Main Site",
                    "pixel_code": "ABCDEF",
                    "status": "NORMAL",
                    "create_time": "2023-01-01",
                    "events": ["Purchase", "ViewContent"],
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_pixels import get_pixels

    result = asyncio.run(get_pixels(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["pixel_id"] == "PX1"
    assert result[0]["events"] == ["Purchase", "ViewContent"]
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"
    assert params["page"] == 1
    assert params["page_size"] == 20


def test_get_pixels_respects_pagination():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_pixels import get_pixels

    asyncio.run(get_pixels(mock_client, advertiser_id="111", page=2, page_size=5))

    params = mock_client._make_request.call_args[0][2]
    assert params["page"] == 2
    assert params["page_size"] == 5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_pixels_returns_pixel_list -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/get_pixels.py`:

```python
"""Get Pixels Tool"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_pixels(
    client,
    advertiser_id: str,
    page: int = 1,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """List all TikTok Pixel installations for an advertiser."""
    params = {"advertiser_id": advertiser_id, "page": page, "page_size": page_size}

    try:
        response = await client._make_request("GET", "/pixel/list/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "pixel_id": item.get("pixel_id"),
                "pixel_name": item.get("pixel_name"),
                "pixel_code": item.get("pixel_code"),
                "status": item.get("status"),
                "create_time": item.get("create_time"),
                "events": item.get("events", []),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get pixels: {e}")
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_pixels_returns_pixel_list tests/test_new_tools.py::test_get_pixels_respects_pagination -v
```

Expected: `2 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

```python
from .get_pixels import get_pixels
```

- [ ] **Step 6: Add server wrapper to `server.py`**

Add `get_pixels` to the import block, then add:

```python
@app.tool()
@handle_errors
async def get_pixels_tool(
    advertiser_id: str,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """List all TikTok Pixel installations for an advertiser. Shows which conversion events
    are being tracked and whether measurement is set up correctly.
    Returns pixel_id, pixel_name, pixel_code, status, create_time, and tracked events."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    pixels = await get_pixels(client, advertiser_id=advertiser_id, page=page, page_size=page_size)
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(pixels), "pixels": pixels},
        indent=2,
    )
```

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/get_pixels.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_pixels tool (TikTok pixel and conversion event listing)"
```

---

## Task 9: `get_smart_plus_campaigns`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_smart_plus_campaigns.py`
- Modify: `tests/test_new_tools.py`
- Modify: `tiktok_ads_mcp/tools/__init__.py`
- Modify: `tiktok_ads_mcp/server.py`

- [ ] **Step 1: Append failing tests**

```python
# ---------------------------------------------------------------------------
# Task 9: get_smart_plus_campaigns
# ---------------------------------------------------------------------------

def test_get_smart_plus_campaigns_returns_campaign_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "campaign_id": "SPC1",
                    "campaign_name": "Smart+ Q1",
                    "status": "ENABLE",
                    "budget": "500.00",
                    "budget_mode": "BUDGET_MODE_DAY",
                    "objective_type": "CONVERSIONS",
                    "create_time": "2024-01-01",
                    "modify_time": "2024-02-01",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_smart_plus_campaigns import get_smart_plus_campaigns

    result = asyncio.run(get_smart_plus_campaigns(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["campaign_id"] == "SPC1"
    assert result[0]["objective_type"] == "CONVERSIONS"
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"


def test_get_smart_plus_campaigns_filters_by_ids():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_smart_plus_campaigns import get_smart_plus_campaigns

    asyncio.run(
        get_smart_plus_campaigns(
            mock_client,
            advertiser_id="111",
            campaign_ids=["SPC1", "SPC2"],
            status="ENABLE",
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["campaign_ids"] == json.dumps(["SPC1", "SPC2"])
    assert params["status"] == "ENABLE"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_smart_plus_campaigns_returns_campaign_list -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement the tool**

Create `tiktok_ads_mcp/tools/get_smart_plus_campaigns.py`:

```python
"""Get Smart+ Campaigns Tool"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def get_smart_plus_campaigns(
    client,
    advertiser_id: str,
    campaign_ids: Optional[List[str]] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> List[Dict[str, Any]]:
    """Get Smart+ (AI-optimised) campaigns — these do not appear in /campaign/get/."""
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "page": page,
        "page_size": page_size,
    }
    if campaign_ids:
        params["campaign_ids"] = json.dumps(campaign_ids)
    if status:
        params["status"] = status

    try:
        response = await client._make_request("GET", "/smart_plus/campaign/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "campaign_id": item.get("campaign_id"),
                "campaign_name": item.get("campaign_name"),
                "status": item.get("status"),
                "budget": item.get("budget"),
                "budget_mode": item.get("budget_mode"),
                "objective_type": item.get("objective_type"),
                "create_time": item.get("create_time"),
                "modify_time": item.get("modify_time"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get Smart+ campaigns: {e}")
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_smart_plus_campaigns_returns_campaign_list tests/test_new_tools.py::test_get_smart_plus_campaigns_filters_by_ids -v
```

Expected: `2 passed`

- [ ] **Step 5: Update `tools/__init__.py`**

```python
from .get_smart_plus_campaigns import get_smart_plus_campaigns
```

The completed `__init__.py` after all 9 tasks should look like:

```python
"""TikTok Ads MCP Tools Package"""

from .get_business_centers import get_business_centers
from .get_authorized_ad_accounts import get_authorized_ad_accounts
from .get_campaigns import get_campaigns
from .get_ad_groups import get_ad_groups
from .get_ads import get_ads
from .reports import get_reports
from .get_advertiser_info import get_advertiser_info
from .get_video_performance import get_video_performance
from .get_creative_fatigue import get_creative_fatigue
from .get_ad_benchmark import get_ad_benchmark
from .async_reports import create_async_report, check_async_report, download_async_report
from .get_audience_reach import get_audience_reach
from .get_targeting_options import get_targeting_options
from .get_pixels import get_pixels
from .get_smart_plus_campaigns import get_smart_plus_campaigns

__all__ = [
    "get_business_centers",
    "get_authorized_ad_accounts",
    "get_campaigns",
    "get_ad_groups",
    "get_ads",
    "get_reports",
    "get_advertiser_info",
    "get_video_performance",
    "get_creative_fatigue",
    "get_ad_benchmark",
    "create_async_report",
    "check_async_report",
    "download_async_report",
    "get_audience_reach",
    "get_targeting_options",
    "get_pixels",
    "get_smart_plus_campaigns",
]
```

- [ ] **Step 6: Add server wrapper to `server.py`**

Add `get_smart_plus_campaigns` to the import block, then add:

```python
@app.tool()
@handle_errors
async def get_smart_plus_campaigns_tool(
    advertiser_id: str,
    campaign_ids: Optional[List[str]] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> str:
    """Get Smart+ (AI-optimised) campaigns for an advertiser.
    Smart+ campaigns do NOT appear in get_campaigns_tool — accounts using Smart+ have a blind spot
    without this tool. Returns campaign_id, name, status, budget, objective_type, create/modify times.
    status filter examples: 'ENABLE', 'DISABLE', 'DELETE'."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    campaigns = await get_smart_plus_campaigns(
        client,
        advertiser_id=advertiser_id,
        campaign_ids=campaign_ids,
        status=status,
        page=page,
        page_size=page_size,
    )
    return json.dumps(
        {
            "success": True,
            "advertiser_id": advertiser_id,
            "count": len(campaigns),
            "campaigns": campaigns,
        },
        indent=2,
    )
```

- [ ] **Step 7: Run complete test suite one final time**

```bash
pytest tests/ -v
```

Expected: all 26 tests pass (8 existing + 18 new).

- [ ] **Step 8: Commit**

```bash
git add tiktok_ads_mcp/tools/get_smart_plus_campaigns.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_smart_plus_campaigns tool (Smart+ AI-optimised campaign coverage)"
```
