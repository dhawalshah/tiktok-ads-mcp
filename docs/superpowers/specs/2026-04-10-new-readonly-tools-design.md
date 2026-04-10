# New Read-Only Tools — Design Spec
**Date:** 2026-04-10
**Scope:** Phase 1 (Core 6) of newly approved TikTok API scopes

## Background

TikTok approved scope changes covering Creative Management (All), Measurement (All), Pixel Management (2 additional APIs), and Ad Account Management (All). This spec covers Phase 1: the six highest-value read-only tools. Phase 2 (creative portfolios, trending content, image assets, BC transactions, BC balance) is deferred until these are verified in production.

The MCP is used both by agencies managing multiple advertisers across Business Centers and by individual advertisers.

## Architecture

Each tool follows the established pattern in this codebase:

1. **Tool module** — `tiktok_ads_mcp/tools/<tool_name>.py`: async function taking `client` + params, returns typed Python data (list or dict). No JSON serialization here.
2. **Server registration** — `server.py`: `@app.tool()` + `@handle_errors` wrapper that validates required params, calls the tool function, and returns `json.dumps(...)`.
3. **Package export** — `tools/__init__.py`: import and `__all__` entry.

No new abstractions or shared utilities needed.

## Tools

### 1. `get_pixel_event_stats`
- **File:** `tiktok_ads_mcp/tools/get_pixel_event_stats.py`
- **Endpoint:** `GET /pixel/event/stats/`
- **Scope:** Pixel Management + Measurement
- **Params:** `advertiser_id` (required), `pixel_ids: List[str]` (required), `start_date: str` (YYYY-MM-DD, required), `end_date: str` (YYYY-MM-DD, required)
- **Returns:** List of records — `pixel_id`, `event_type`, `date`, `count`, `match_rate`
- **Purpose:** See how many conversion events (Purchase, AddToCart, ViewContent, etc.) each pixel is recording over a date range. Critical for verifying measurement health.

### 2. `get_video_assets`
- **File:** `tiktok_ads_mcp/tools/get_video_assets.py`
- **Endpoint:** `GET /file/video/ad/search/`
- **Scope:** Creative Management
- **Params:** `advertiser_id` (required), `filtering: Dict` (optional), `page: int` (default 1), `page_size: int` (default 20)
- **Returns:** List of — `video_id`, `video_name`, `duration`, `width`, `height`, `cover_url`, `create_time`, `size`
- **Purpose:** Browse the creative asset library to see what video creatives are available for use in ads.

### 3. `get_advertiser_balance`
- **File:** `tiktok_ads_mcp/tools/get_advertiser_balance.py`
- **Endpoint:** `GET /advertiser/balance/get/`
- **Scope:** Ad Account Management
- **Params:** `bc_id` (required)
- **Returns:** List of — `advertiser_id`, `balance`, `credit_limit`, `currency`
- **Purpose:** Check remaining budget across all advertiser accounts in a Business Center. Key for agency billing oversight.

### 4. `get_bc_assets`
- **File:** `tiktok_ads_mcp/tools/get_bc_assets.py`
- **Endpoint:** `GET /bc/asset/get/`
- **Scope:** Ad Account Management
- **Params:** `bc_id` (required), `asset_type: str` (required — `ADVERTISER` | `PIXEL` | `CATALOG`)
- **Returns:** List of — `asset_id`, `asset_name`, `asset_type`, `status`
- **Purpose:** Inventory all assets within a Business Center by type. Useful for agencies auditing what's under management.

### 5. `get_bc_members`
- **File:** `tiktok_ads_mcp/tools/get_bc_members.py`
- **Endpoint:** `GET /bc/member/get/`
- **Scope:** Ad Account Management
- **Params:** `bc_id` (required)
- **Returns:** List of — `user_id`, `username`, `email`, `role`, `status`
- **Purpose:** See who has access to a Business Center and what role they hold. Useful for access audits.

### 6. `get_offline_event_sets`
- **File:** `tiktok_ads_mcp/tools/get_offline_event_sets.py`
- **Endpoint:** `GET /offline/get/`
- **Scope:** Measurement
- **Params:** `advertiser_id` (required)
- **Returns:** List of — `event_set_id`, `name`, `status`, `event_types`, `create_time`
- **Purpose:** List offline conversion sets configured for an advertiser. Shows what offline events (e.g. in-store purchases) are being matched.

## Error Handling

Same as existing tools — exceptions propagate up to the `@handle_errors` decorator in `server.py`, which returns a structured error JSON. No tool-level try/catch beyond what's needed for field extraction.

## Testing

Smoke-test each tool against a live advertiser ID using `smoke_test.py` or a standalone probe script, following the pattern in `probe_apis.py`. No unit tests planned (consistent with existing test approach).

## Phase 2 (deferred)

- `get_creative_portfolios` — `GET /creative/portfolio/list/`
- `get_trending_content` — `GET /discovery/trending_list/` + `GET /discovery/detail/`
- `get_image_assets` — `GET /file/image/ad/info/`
- `get_bc_transactions` — `GET /bc/transaction/get/`
- `get_bc_balance` — `GET /bc/balance/get/`
