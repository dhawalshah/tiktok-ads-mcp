# Phase 1 Read-Only Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add six new read-only MCP tools covering pixel event stats, video assets, advertiser balance, BC assets, BC members, and offline event sets.

**Architecture:** Each tool follows the established three-file pattern: a pure async function in `tools/<name>.py`, a `@app.tool()` wrapper in `server.py`, and an export in `tools/__init__.py`. Tests mock `client._make_request` with `AsyncMock` and run via `asyncio.run()`.

**Tech Stack:** Python, FastMCP, httpx, asyncio, pytest

---

## File Map

| Action | File |
|--------|------|
| Create | `tiktok_ads_mcp/tools/get_pixel_event_stats.py` |
| Create | `tiktok_ads_mcp/tools/get_video_assets.py` |
| Create | `tiktok_ads_mcp/tools/get_advertiser_balance.py` |
| Create | `tiktok_ads_mcp/tools/get_bc_assets.py` |
| Create | `tiktok_ads_mcp/tools/get_bc_members.py` |
| Create | `tiktok_ads_mcp/tools/get_offline_event_sets.py` |
| Modify | `tiktok_ads_mcp/tools/__init__.py` |
| Modify | `tiktok_ads_mcp/server.py` |
| Modify | `tests/test_new_tools.py` |

---

## Task 1: `get_pixel_event_stats`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_pixel_event_stats.py`
- Modify: `tests/test_new_tools.py` (append tests)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_new_tools.py`:

```python
# ---------------------------------------------------------------------------
# get_pixel_event_stats
# ---------------------------------------------------------------------------

def test_get_pixel_event_stats_returns_event_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "pixel_id": "PX1",
                    "event_type": "Purchase",
                    "date": "2024-01-01",
                    "count": 42,
                    "match_rate": 0.85,
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_pixel_event_stats import get_pixel_event_stats

    result = asyncio.run(
        get_pixel_event_stats(
            mock_client,
            advertiser_id="111",
            pixel_ids=["PX1"],
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    )

    assert len(result) == 1
    assert result[0]["pixel_id"] == "PX1"
    assert result[0]["event_type"] == "Purchase"
    assert result[0]["count"] == 42
    assert result[0]["match_rate"] == 0.85
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"
    assert params["pixel_ids"] == json.dumps(["PX1"])
    assert params["start_date"] == "2024-01-01"
    assert params["end_date"] == "2024-01-31"


def test_get_pixel_event_stats_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_pixel_event_stats import get_pixel_event_stats

    result = asyncio.run(
        get_pixel_event_stats(
            mock_client,
            advertiser_id="111",
            pixel_ids=["PX1"],
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    )
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/dhawal/src/team-mcp/tiktok-ads-mcp
pytest tests/test_new_tools.py::test_get_pixel_event_stats_returns_event_list tests/test_new_tools.py::test_get_pixel_event_stats_empty_response -v
```

Expected: `ModuleNotFoundError` or `ImportError` — the module doesn't exist yet.

- [ ] **Step 3: Create `tiktok_ads_mcp/tools/get_pixel_event_stats.py`**

```python
"""Get Pixel Event Stats Tool"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_pixel_event_stats(
    client,
    advertiser_id: str,
    pixel_ids: List[str],
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """Get aggregated conversion event counts per pixel over a date range."""
    params: Dict[str, Any] = {
        "advertiser_id": advertiser_id,
        "pixel_ids": json.dumps(pixel_ids),
        "start_date": start_date,
        "end_date": end_date,
    }

    try:
        response = await client._make_request("GET", "/pixel/event/stats/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "pixel_id": item.get("pixel_id"),
                "event_type": item.get("event_type"),
                "date": item.get("date"),
                "count": item.get("count"),
                "match_rate": item.get("match_rate"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get pixel event stats: {e}")
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_pixel_event_stats_returns_event_list tests/test_new_tools.py::test_get_pixel_event_stats_empty_response -v
```

Expected: both PASS.

- [ ] **Step 5: Export from `tools/__init__.py`** — add to imports and `__all__`:

```python
from .get_pixel_event_stats import get_pixel_event_stats
```

And add `"get_pixel_event_stats"` to the `__all__` list.

- [ ] **Step 6: Register tool in `server.py`** — add import at the top with the other tool imports:

```python
from .tools import (
    ...
    get_pixel_event_stats,
)
```

Then add the tool function after the `get_pixels_tool` block:

```python
@app.tool()
@handle_errors
async def get_pixel_event_stats_tool(
    advertiser_id: str,
    pixel_ids: List[str],
    start_date: str,
    end_date: str,
) -> str:
    """Get aggregated conversion event counts (Purchase, AddToCart, ViewContent, etc.)
    per pixel over a date range. Use after get_pixels_tool to get pixel_ids.
    Dates are YYYY-MM-DD. Returns one row per pixel per event type per day."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    if not pixel_ids:
        raise ValueError("pixel_ids is required")
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required")
    client = get_tiktok_client()
    items = await get_pixel_event_stats(
        client,
        advertiser_id=advertiser_id,
        pixel_ids=pixel_ids,
        start_date=start_date,
        end_date=end_date,
    )
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(items), "events": items},
        indent=2,
    )
```

- [ ] **Step 7: Commit**

```bash
git add tiktok_ads_mcp/tools/get_pixel_event_stats.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_pixel_event_stats tool"
```

---

## Task 2: `get_video_assets`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_video_assets.py`
- Modify: `tests/test_new_tools.py` (append tests)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_new_tools.py`:

```python
# ---------------------------------------------------------------------------
# get_video_assets
# ---------------------------------------------------------------------------

def test_get_video_assets_returns_video_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "videos": [
                {
                    "video_id": "V1",
                    "file_name": "Summer Ad",
                    "duration": 15,
                    "width": 1080,
                    "height": 1920,
                    "poster_url": "https://example.com/cover.jpg",
                    "create_time": 1704067200,
                    "size": 5242880,
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_video_assets import get_video_assets

    result = asyncio.run(get_video_assets(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["video_id"] == "V1"
    assert result[0]["video_name"] == "Summer Ad"
    assert result[0]["duration"] == 15
    assert result[0]["width"] == 1080
    assert result[0]["height"] == 1920
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"
    assert params["page"] == 1
    assert params["page_size"] == 20


def test_get_video_assets_passes_filtering():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"videos": []}}

    from tiktok_ads_mcp.tools.get_video_assets import get_video_assets

    asyncio.run(
        get_video_assets(
            mock_client,
            advertiser_id="111",
            filtering={"video_name": "Summer"},
            page=2,
            page_size=10,
        )
    )

    params = mock_client._make_request.call_args[0][2]
    assert params["filtering"] == json.dumps({"video_name": "Summer"})
    assert params["page"] == 2
    assert params["page_size"] == 10
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_video_assets_returns_video_list tests/test_new_tools.py::test_get_video_assets_passes_filtering -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `tiktok_ads_mcp/tools/get_video_assets.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_video_assets_returns_video_list tests/test_new_tools.py::test_get_video_assets_passes_filtering -v
```

Expected: both PASS.

- [ ] **Step 5: Export from `tools/__init__.py`**

Add `from .get_video_assets import get_video_assets` to imports and `"get_video_assets"` to `__all__`.

- [ ] **Step 6: Register tool in `server.py`** — add to imports, then add after `get_pixel_event_stats_tool`:

```python
@app.tool()
@handle_errors
async def get_video_assets_tool(
    advertiser_id: str,
    filtering: Dict = None,
    page: int = 1,
    page_size: int = 20,
) -> str:
    """Browse the creative video asset library for an advertiser.
    Returns video_id, video_name, duration, width, height, cover_url, create_time, size.
    Optional filtering dict supports keys like 'video_name' for name search."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    items = await get_video_assets(
        client,
        advertiser_id=advertiser_id,
        filtering=filtering,
        page=page,
        page_size=page_size,
    )
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(items), "videos": items},
        indent=2,
    )
```

- [ ] **Step 7: Commit**

```bash
git add tiktok_ads_mcp/tools/get_video_assets.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_video_assets tool"
```

---

## Task 3: `get_advertiser_balance`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_advertiser_balance.py`
- Modify: `tests/test_new_tools.py` (append tests)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_new_tools.py`:

```python
# ---------------------------------------------------------------------------
# get_advertiser_balance
# ---------------------------------------------------------------------------

def test_get_advertiser_balance_returns_balance_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "advertiser_id": "111",
                    "balance": "1500.00",
                    "credit_limit": "5000.00",
                    "currency": "USD",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_advertiser_balance import get_advertiser_balance

    result = asyncio.run(get_advertiser_balance(mock_client, bc_id="BC1"))

    assert len(result) == 1
    assert result[0]["advertiser_id"] == "111"
    assert result[0]["balance"] == "1500.00"
    assert result[0]["credit_limit"] == "5000.00"
    assert result[0]["currency"] == "USD"
    params = mock_client._make_request.call_args[0][2]
    assert params["bc_id"] == "BC1"


def test_get_advertiser_balance_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_advertiser_balance import get_advertiser_balance

    result = asyncio.run(get_advertiser_balance(mock_client, bc_id="BC1"))
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_advertiser_balance_returns_balance_list tests/test_new_tools.py::test_get_advertiser_balance_empty_response -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `tiktok_ads_mcp/tools/get_advertiser_balance.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_advertiser_balance_returns_balance_list tests/test_new_tools.py::test_get_advertiser_balance_empty_response -v
```

Expected: both PASS.

- [ ] **Step 5: Export from `tools/__init__.py`**

Add `from .get_advertiser_balance import get_advertiser_balance` to imports and `"get_advertiser_balance"` to `__all__`.

- [ ] **Step 6: Register tool in `server.py`** — add to imports, then append:

```python
@app.tool()
@handle_errors
async def get_advertiser_balance_tool(bc_id: str) -> str:
    """Get cash balance and credit limit for all advertiser accounts within a Business Center.
    Returns advertiser_id, balance, credit_limit, and currency for each account.
    Use get_business_centers_tool first to get bc_id."""
    if not bc_id:
        raise ValueError("bc_id is required")
    client = get_tiktok_client()
    items = await get_advertiser_balance(client, bc_id=bc_id)
    return json.dumps(
        {"success": True, "bc_id": bc_id, "count": len(items), "balances": items},
        indent=2,
    )
```

- [ ] **Step 7: Commit**

```bash
git add tiktok_ads_mcp/tools/get_advertiser_balance.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_advertiser_balance tool"
```

---

## Task 4: `get_bc_assets`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_bc_assets.py`
- Modify: `tests/test_new_tools.py` (append tests)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_new_tools.py`:

```python
# ---------------------------------------------------------------------------
# get_bc_assets
# ---------------------------------------------------------------------------

def test_get_bc_assets_returns_asset_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "asset_id": "A1",
                    "asset_name": "Main Account",
                    "asset_type": "ADVERTISER",
                    "status": "ENABLE",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_bc_assets import get_bc_assets

    result = asyncio.run(get_bc_assets(mock_client, bc_id="BC1", asset_type="ADVERTISER"))

    assert len(result) == 1
    assert result[0]["asset_id"] == "A1"
    assert result[0]["asset_name"] == "Main Account"
    assert result[0]["asset_type"] == "ADVERTISER"
    assert result[0]["status"] == "ENABLE"
    params = mock_client._make_request.call_args[0][2]
    assert params["bc_id"] == "BC1"
    assert params["asset_type"] == "ADVERTISER"


def test_get_bc_assets_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_bc_assets import get_bc_assets

    result = asyncio.run(get_bc_assets(mock_client, bc_id="BC1", asset_type="PIXEL"))
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_bc_assets_returns_asset_list tests/test_new_tools.py::test_get_bc_assets_empty_response -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `tiktok_ads_mcp/tools/get_bc_assets.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_bc_assets_returns_asset_list tests/test_new_tools.py::test_get_bc_assets_empty_response -v
```

Expected: both PASS.

- [ ] **Step 5: Export from `tools/__init__.py`**

Add `from .get_bc_assets import get_bc_assets` to imports and `"get_bc_assets"` to `__all__`.

- [ ] **Step 6: Register tool in `server.py`** — add to imports, then append:

```python
@app.tool()
@handle_errors
async def get_bc_assets_tool(bc_id: str, asset_type: str) -> str:
    """Get all assets of a given type within a Business Center.
    asset_type must be one of: ADVERTISER, PIXEL, CATALOG.
    Returns asset_id, asset_name, asset_type, status for each asset.
    Use get_business_centers_tool first to get bc_id."""
    if not bc_id:
        raise ValueError("bc_id is required")
    if not asset_type:
        raise ValueError("asset_type is required — use ADVERTISER, PIXEL, or CATALOG")
    client = get_tiktok_client()
    items = await get_bc_assets(client, bc_id=bc_id, asset_type=asset_type)
    return json.dumps(
        {"success": True, "bc_id": bc_id, "asset_type": asset_type, "count": len(items), "assets": items},
        indent=2,
    )
```

- [ ] **Step 7: Commit**

```bash
git add tiktok_ads_mcp/tools/get_bc_assets.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_bc_assets tool"
```

---

## Task 5: `get_bc_members`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_bc_members.py`
- Modify: `tests/test_new_tools.py` (append tests)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_new_tools.py`:

```python
# ---------------------------------------------------------------------------
# get_bc_members
# ---------------------------------------------------------------------------

def test_get_bc_members_returns_member_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "user_id": "U1",
                    "username": "jane_doe",
                    "email": "jane@example.com",
                    "role": "ADMIN",
                    "status": "ACTIVE",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_bc_members import get_bc_members

    result = asyncio.run(get_bc_members(mock_client, bc_id="BC1"))

    assert len(result) == 1
    assert result[0]["user_id"] == "U1"
    assert result[0]["username"] == "jane_doe"
    assert result[0]["role"] == "ADMIN"
    params = mock_client._make_request.call_args[0][2]
    assert params["bc_id"] == "BC1"


def test_get_bc_members_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_bc_members import get_bc_members

    result = asyncio.run(get_bc_members(mock_client, bc_id="BC1"))
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_bc_members_returns_member_list tests/test_new_tools.py::test_get_bc_members_empty_response -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `tiktok_ads_mcp/tools/get_bc_members.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_bc_members_returns_member_list tests/test_new_tools.py::test_get_bc_members_empty_response -v
```

Expected: both PASS.

- [ ] **Step 5: Export from `tools/__init__.py`**

Add `from .get_bc_members import get_bc_members` to imports and `"get_bc_members"` to `__all__`.

- [ ] **Step 6: Register tool in `server.py`** — add to imports, then append:

```python
@app.tool()
@handle_errors
async def get_bc_members_tool(bc_id: str) -> str:
    """Get all members of a Business Center, their roles, and access status.
    Returns user_id, username, email, role, status for each member.
    Useful for access audits. Use get_business_centers_tool first to get bc_id."""
    if not bc_id:
        raise ValueError("bc_id is required")
    client = get_tiktok_client()
    items = await get_bc_members(client, bc_id=bc_id)
    return json.dumps(
        {"success": True, "bc_id": bc_id, "count": len(items), "members": items},
        indent=2,
    )
```

- [ ] **Step 7: Commit**

```bash
git add tiktok_ads_mcp/tools/get_bc_members.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_bc_members tool"
```

---

## Task 6: `get_offline_event_sets`

**Files:**
- Create: `tiktok_ads_mcp/tools/get_offline_event_sets.py`
- Modify: `tests/test_new_tools.py` (append tests)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_new_tools.py`:

```python
# ---------------------------------------------------------------------------
# get_offline_event_sets
# ---------------------------------------------------------------------------

def test_get_offline_event_sets_returns_set_list():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {
        "code": 0,
        "data": {
            "list": [
                {
                    "event_set_id": "ES1",
                    "name": "In-store Purchases",
                    "status": "ENABLE",
                    "event_types": ["Purchase", "Lead"],
                    "create_time": "2024-01-01",
                }
            ]
        },
    }

    from tiktok_ads_mcp.tools.get_offline_event_sets import get_offline_event_sets

    result = asyncio.run(get_offline_event_sets(mock_client, advertiser_id="111"))

    assert len(result) == 1
    assert result[0]["event_set_id"] == "ES1"
    assert result[0]["name"] == "In-store Purchases"
    assert result[0]["event_types"] == ["Purchase", "Lead"]
    params = mock_client._make_request.call_args[0][2]
    assert params["advertiser_id"] == "111"


def test_get_offline_event_sets_empty_response():
    mock_client = AsyncMock()
    mock_client._make_request.return_value = {"code": 0, "data": {"list": []}}

    from tiktok_ads_mcp.tools.get_offline_event_sets import get_offline_event_sets

    result = asyncio.run(get_offline_event_sets(mock_client, advertiser_id="111"))
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_new_tools.py::test_get_offline_event_sets_returns_set_list tests/test_new_tools.py::test_get_offline_event_sets_empty_response -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `tiktok_ads_mcp/tools/get_offline_event_sets.py`**

```python
"""Get Offline Event Sets Tool"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def get_offline_event_sets(
    client,
    advertiser_id: str,
) -> List[Dict[str, Any]]:
    """List offline conversion event sets configured for an advertiser."""
    params: Dict[str, Any] = {"advertiser_id": advertiser_id}

    try:
        response = await client._make_request("GET", "/offline/get/", params)
        items = response.get("data", {}).get("list", [])
        return [
            {
                "event_set_id": item.get("event_set_id"),
                "name": item.get("name"),
                "status": item.get("status"),
                "event_types": item.get("event_types", []),
                "create_time": item.get("create_time"),
            }
            for item in items
        ]
    except Exception as e:
        logger.error(f"Failed to get offline event sets: {e}")
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_new_tools.py::test_get_offline_event_sets_returns_set_list tests/test_new_tools.py::test_get_offline_event_sets_empty_response -v
```

Expected: both PASS.

- [ ] **Step 5: Export from `tools/__init__.py`**

Add `from .get_offline_event_sets import get_offline_event_sets` to imports and `"get_offline_event_sets"` to `__all__`.

- [ ] **Step 6: Register tool in `server.py`** — add to imports, then append:

```python
@app.tool()
@handle_errors
async def get_offline_event_sets_tool(advertiser_id: str) -> str:
    """List offline conversion event sets configured for an advertiser.
    Shows what offline events (e.g. in-store purchases, phone leads) are being
    matched back to TikTok ad exposure. Returns event_set_id, name, status,
    event_types, and create_time."""
    if not advertiser_id:
        raise ValueError("advertiser_id is required")
    client = get_tiktok_client()
    items = await get_offline_event_sets(client, advertiser_id=advertiser_id)
    return json.dumps(
        {"success": True, "advertiser_id": advertiser_id, "count": len(items), "event_sets": items},
        indent=2,
    )
```

- [ ] **Step 7: Commit**

```bash
git add tiktok_ads_mcp/tools/get_offline_event_sets.py tiktok_ads_mcp/tools/__init__.py tiktok_ads_mcp/server.py tests/test_new_tools.py
git commit -m "feat: add get_offline_event_sets tool"
```

---

## Task 7: Full Test Run

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass. If any fail, fix the specific failure before proceeding.

- [ ] **Step 2: Verify tool count in server**

```bash
grep -c "@app.tool()" tiktok_ads_mcp/server.py
```

Expected: `22` (16 existing + 6 new).

- [ ] **Step 3: Commit if any fixes were needed, otherwise done**

```bash
git add -A
git commit -m "fix: address any issues found in full test run"
```

Only run this step if fixes were made in Step 1.
