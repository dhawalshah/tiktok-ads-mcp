# New Tools Expansion Design

**Date:** 2026-04-08
**Status:** Approved

---

## Goal

Add 12 new read-only MCP tools covering the full set of approved TikTok API scopes (Ad Account Management, Ads Management, Reporting, Measurement, Creative Management). The 6 existing tools cover only the basic campaign hierarchy read + integrated reports. This expansion adds account info, TikTok-specific video metrics, creative insights, async reporting, audience planning, and Smart+ campaigns.

---

## Approved scopes being leveraged

- Ad Account Management → `get_advertiser_info_tool`
- Reporting → video performance, ad benchmark, async reports
- Creative Management → creative fatigue
- Measurement → pixels
- Ads Management (read) → Smart+ campaigns, targeting options, audience reach

---

## Architecture

Same pattern as all existing tools throughout. No new dependencies, no new design patterns:

1. **One file per tool** in `tiktok_ads_mcp/tools/` — pure async function taking `client` + params, returning a list or dict
2. **`@app.tool()` wrapper in `server.py`** — validates required params, calls tool function, wraps in standard `{success, ...}` JSON envelope
3. **`tools/__init__.py`** updated with each new import
4. **Error handling** via existing `@handle_errors` decorator on server.py wrappers

---

## New Files

| File | Tools inside |
|---|---|
| `tiktok_ads_mcp/tools/get_advertiser_info.py` | `get_advertiser_info` |
| `tiktok_ads_mcp/tools/get_video_performance.py` | `get_video_performance` |
| `tiktok_ads_mcp/tools/get_creative_fatigue.py` | `get_creative_fatigue` |
| `tiktok_ads_mcp/tools/get_ad_benchmark.py` | `get_ad_benchmark` |
| `tiktok_ads_mcp/tools/async_reports.py` | `create_async_report`, `check_async_report`, `download_async_report` |
| `tiktok_ads_mcp/tools/get_audience_reach.py` | `get_audience_reach` |
| `tiktok_ads_mcp/tools/get_targeting_options.py` | `get_targeting_options` |
| `tiktok_ads_mcp/tools/get_pixels.py` | `get_pixels` |
| `tiktok_ads_mcp/tools/get_smart_plus_campaigns.py` | `get_smart_plus_campaigns` |

---

## Tool Specifications

### 1. `get_advertiser_info_tool`

**File:** `get_advertiser_info.py`
**Endpoint:** `GET /advertiser/info/`
**Purpose:** Account-level metadata — currency, timezone, industry, budget, status. Foundation for interpreting all other data correctly (especially date breakdowns which depend on account timezone).

**Tool function signature:**
```python
async def get_advertiser_info(client, advertiser_ids: List[str]) -> List[Dict]
```

**Server wrapper inputs:** `advertiser_ids: List[str]`

**Returns fields:** `advertiser_id`, `name`, `currency`, `timezone`, `industry`, `status`, `description`, `phone_number`, `address`, `contacter`

---

### 2. `get_video_performance_tool`

**File:** `get_video_performance.py`
**Endpoint:** `GET /report/video_performance/get/`
**Purpose:** TikTok-specific video engagement metrics not available in the integrated report: 2-second views, 6-second views, completion rate, average watch time, video play actions. Critical for understanding creative performance on TikTok specifically.

**Tool function signature:**
```python
async def get_video_performance(
    client,
    advertiser_id: str,
    data_level: str = "AUCTION_AD",  # AUCTION_AD | AUCTION_ADGROUP | AUCTION_CAMPAIGN
    start_date: Optional[str] = None,   # YYYY-MM-DD
    end_date: Optional[str] = None,
    dimensions: Optional[List[str]] = None,  # e.g. ["ad_id", "stat_time_day"]
    page: int = 1,
    page_size: int = 10
) -> Dict
```

**Returns:** `list` of rows with video metrics, `page_info`

---

### 3. `get_creative_fatigue_tool`

**File:** `get_creative_fatigue.py`
**Endpoint:** `GET /creative_fatigue/get/`
**Purpose:** Returns creative fatigue score per ad. Indicates when an ad has been shown too frequently to the same audience and needs refreshing. Actionable for creative planning.

**Tool function signature:**
```python
async def get_creative_fatigue(
    client,
    advertiser_id: str,
    ad_ids: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 20
) -> List[Dict]
```

**Returns fields per ad:** `ad_id`, `ad_name`, `fatigue_status`, `fatigue_level`, `recommendation`

---

### 4. `get_ad_benchmark_tool`

**File:** `get_ad_benchmark.py`
**Endpoint:** `GET /report/ad_benchmark/get/`
**Purpose:** Industry benchmark metrics (CTR, CVR, CPM, CPC) by vertical and placement. Used to evaluate whether account performance is above/below industry average.

**Tool function signature:**
```python
async def get_ad_benchmark(
    client,
    advertiser_id: str,
    industry_id: Optional[str] = None,
    placement_type: Optional[str] = None,  # e.g. "PLACEMENT_TIKTOK"
    objective_type: Optional[str] = None
) -> Dict
```

**Returns:** benchmark metrics dict with industry/placement context

---

### 5. Async Report Workflow — 3 tools in `async_reports.py`

**Purpose:** The synchronous `/report/integrated/get/` has row limits and date range caps. For large accounts or long date ranges, async task reports are required.

**Workflow guidance is embedded in tool docstrings** so Claude orchestrates the 3-step flow automatically when a user asks for large report data.

#### `create_async_report_tool`

**Endpoint:** `POST /report/task/create/`

**Docstring (shown to Claude):**
> Creates an async report task for large datasets or long date ranges. After calling this tool, **immediately use `check_async_report_tool` with the returned `task_id` to monitor progress. When status is COMPLETE, use `download_async_report_tool` to retrieve the data.** Inform the user that the report is being generated and you will check on it.

**Inputs:** `advertiser_id`, `report_type`, `data_level`, `dimensions`, `metrics`, `start_date`, `end_date`
**Returns:** `{task_id, status}`

#### `check_async_report_tool`

**Endpoint:** `GET /report/task/check/`

**Docstring:**
> Checks the status of an async report task created by `create_async_report_tool`. Status will be PROCESSING, COMPLETE, or FAILED. **If PROCESSING, inform the user it is still generating and check again shortly. When COMPLETE, call `download_async_report_tool` with the same `task_id`.**

**Inputs:** `advertiser_id`, `task_id`
**Returns:** `{task_id, status, progress_rate}`

#### `download_async_report_tool`

**Endpoint:** `GET /report/task/download/` (may return a download URL; client fetches data from URL)

**Docstring:**
> Downloads the completed data for an async report task. **Only call after `check_async_report_tool` returns status COMPLETE.** Returns the report rows.

**Inputs:** `advertiser_id`, `task_id`
**Returns:** report rows list

**Implementation note:** The download endpoint may return a URL rather than inline data. The tool function should detect this and follow the URL to return actual rows to the caller.

---

### 6. `get_audience_reach_tool`

**File:** `get_audience_reach.py`
**Endpoint:** `GET /tool/reach/forecast/` *(verify exact path against TikTok docs during implementation)*
**Purpose:** Estimated audience reach for given targeting criteria. Useful for planning campaigns and understanding audience size before launch.

**Tool function signature:**
```python
async def get_audience_reach(
    client,
    advertiser_id: str,
    objective_type: str,                # e.g. "TRAFFIC", "CONVERSIONS"
    placements: Optional[List[str]] = None,
    age: Optional[List[str]] = None,
    gender: Optional[str] = None,       # "GENDER_MALE", "GENDER_FEMALE", "GENDER_UNLIMITED"
    location_ids: Optional[List[str]] = None,
    interest_category_ids: Optional[List[str]] = None,
) -> Dict
```

**Returns:** `{estimated_audience_size_lower, estimated_audience_size_upper, reach_trend}`

---

### 7. `get_targeting_options_tool`

**File:** `get_targeting_options.py`
**Endpoint:** `GET /tool/targeting/search/` *(verify exact path during implementation)*
**Purpose:** Search available targeting options (interests, behaviors, demographics) by keyword. Helps Claude answer questions like "what TikTok interest categories exist for fitness brands?"

**Tool function signature:**
```python
async def get_targeting_options(
    client,
    advertiser_id: str,
    query: str,                          # search keyword
    objective_type: Optional[str] = None,
    targeting_type: Optional[str] = None # "INTEREST", "BEHAVIOR", etc.
) -> List[Dict]
```

**Returns:** list of matching targeting options with `id`, `name`, `type`, `audience_size`

---

### 8. `get_pixels_tool`

**File:** `get_pixels.py`
**Endpoint:** `GET /pixel/list/` *(verify exact path during implementation)*
**Purpose:** List all TikTok Pixel installations for an advertiser. Important context for understanding which conversion events are being tracked and whether measurement is set up correctly.

**Tool function signature:**
```python
async def get_pixels(
    client,
    advertiser_id: str,
    page: int = 1,
    page_size: int = 20
) -> List[Dict]
```

**Returns fields per pixel:** `pixel_id`, `pixel_name`, `pixel_code`, `status`, `create_time`, `events` (list of tracked events)

---

### 9. `get_smart_plus_campaigns_tool`

**File:** `get_smart_plus_campaigns.py`
**Endpoint:** `GET /smart_plus/campaign/get/`
**Purpose:** Retrieve Smart+ (AI-optimised) campaigns. These do not appear in the regular `/campaign/get/` response, so accounts using Smart+ have a blind spot in the current tool coverage.

**Tool function signature:**
```python
async def get_smart_plus_campaigns(
    client,
    advertiser_id: str,
    campaign_ids: Optional[List[str]] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> List[Dict]
```

**Returns fields:** `campaign_id`, `campaign_name`, `status`, `budget`, `budget_mode`, `objective_type`, `create_time`, `modify_time`

---

## Changes to Existing Files

| File | Change |
|---|---|
| `tiktok_ads_mcp/tools/__init__.py` | Add 12 new imports |
| `tiktok_ads_mcp/server.py` | Add 12 new `@app.tool()` wrappers |

`server.py` grows by ~150 lines. It's already 235 lines for 6 tools — at ~385 lines for 18 tools it remains manageable and consistent with the existing pattern. No refactoring needed.

---

## Out of Scope

- Write operations (create/update/delete) — project is read-only by design
- GMV Max reports, Smart+ material reports — niche, low priority for now
- Report subscription endpoints — not needed for on-demand querying
- Campaign copy, SPC campaigns — operational, not analytics
