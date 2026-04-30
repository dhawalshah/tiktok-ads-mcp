# TikTok Ads MCP

A Model Context Protocol (MCP) server for the TikTok Business API. Connect Claude (or any MCP-compatible AI client) directly to your TikTok ad accounts to query campaigns, video performance, audience targeting, benchmarks, and more — all in natural language.

The server speaks the [MCP authorization spec (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization), so it works as a remote connector anywhere Claude supports custom MCP servers — claude.ai (personal), Claude Desktop, and Claude Teams. Add **one URL**, click "Connect", sign in with TikTok, done. For a Teams plan, the org owner adds the URL once and each member individually authenticates on first use.

## What you can do

### Account & Business Center
- List authorized advertiser accounts under your TikTok identity
- Get advertiser metadata (currency, timezone, industry, status)
- List Business Centers, BC members, and BC assets

### Campaigns, Ad Groups & Ads
- List standard campaigns and Smart+ (AI-optimised) campaigns
- List ad groups and individual ads with creatives and status
- Inspect video assets and creative fatigue scores

### Reporting & Performance
- Custom reports with any TikTok dimensions and metrics over any date range
- Video-specific metrics (2s/6s views, completion rate, average watch time)
- Ad benchmark comparisons against industry CTR/CVR/CPM/CPC
- Async reports for large date ranges (partner-programme tools)

### Audience, Pixels, Conversions
- Browse all interest categories for audience targeting
- Audience reach estimates
- List TikTok Pixel installs + conversion event stats
- List offline event sets

### Account Operations
- Advertiser balance for the authorised account

---

## How auth works

There are **two** modes. Pick one.

### Mode A — Local STDIO (one user, no server)
Use this if you only want it on your own machine. Run the included one-shot OAuth flow (`get_token.py` / `catch_auth.py`) once, set `TIKTOK_ACCESS_TOKEN` in your env, and Claude Desktop launches the server as a subprocess. No Firestore, no Cloud Run, no public URL.

### Mode B — Remote HTTP server (Claude Teams, claude.ai, multi-user)
The MCP server is also an OAuth 2.1 authorization server. When Claude connects:

1. Claude discovers our metadata at `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server`.
2. Claude registers itself via Dynamic Client Registration (`POST /oauth/register`).
3. Claude redirects the user to `/oauth/authorize`. We delegate identification to TikTok Business OAuth.
4. After TikTok login, we issue our **own** opaque bearer token to Claude — TikTok credentials never leave the server.
5. On each `/mcp` request Claude sends our bearer; we map it server-side to the right user's stored TikTok credentials and call the TikTok Business APIs.

> **A note on access control.** TikTok returns whatever email the user signed up with — usually personal (gmail, hotmail, etc.) rather than work email. Domain-based restriction therefore isn't reliable. By default this MCP allows any TikTok Business user to connect; the security comes from TikTok's own permission model (each user only sees ad accounts their TikTok profile has been authorised for). For tighter control, set `ALLOWED_EMAILS` to a comma-separated allow-list of TikTok-account emails.

---

## Prerequisites

- Python 3.10+
- A TikTok Business app with at least one advertiser authorised
- A [Google Cloud](https://console.cloud.google.com/) project (Mode B only)

---

## Step 1 — Create a TikTok Developer App

1. Go to the [TikTok Business API Developer Portal](https://business-api.tiktok.com/portal/) and create an app.
2. Note your **App ID** and **Secret** (used as the OAuth client credentials).
3. Under **Advertiser redirect URLs**, add:
   - `http://localhost:8080/oauth/callback` *(local dev)*
   - `https://YOUR-CLOUD-RUN-URL/oauth/callback` *(Mode B — add after deploy)*
4. Note: TikTok shows a 10-minute propagation delay for new redirect URLs.

---

## Step 2 — Install

```bash
git clone https://github.com/dhawalshah/tiktok-ads-mcp
cd tiktok-ads-mcp
pip install -r requirements.txt
cp env.template .env       # fill in values
```

---

## Step 3 — Mode A: Local STDIO

Run the one-shot OAuth flow (visits TikTok, captures the auth_code, exchanges for tokens):

```bash
python catch_auth.py        # opens browser, prints access_token
# Copy the access_token into .env as TIKTOK_ACCESS_TOKEN
```

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "tiktok-ads": {
      "command": "tiktok-ads-mcp",
      "env": {
        "TIKTOK_APP_ID": "your_app_id",
        "TIKTOK_SECRET": "your_app_secret",
        "TIKTOK_ACCESS_TOKEN": "your_access_token"
      }
    }
  }
}
```

Restart Claude Desktop. You're done — skip the rest.

---

## Step 3 — Mode B: Remote HTTP server (Claude Teams / claude.ai)

### Enable Firestore
The server stores OAuth bearer tokens and per-user TikTok credentials in Firestore.
1. In Cloud Console, **Firestore → Create database → Native mode**, pick a region.
2. Grant the Cloud Run service account **Cloud Datastore User** role under **IAM & Admin → IAM**.

### Deploy to Cloud Run

```bash
gcloud run deploy tiktok-ads-mcp \
  --source . \
  --region YOUR_REGION \
  --project YOUR_PROJECT_ID \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=your-project-id,BASE_URL=https://YOUR-SERVICE-URL.run.app,TIKTOK_APP_ID=...,TIKTOK_SECRET=..."
```

> **Recommended:** store `TIKTOK_SECRET` in Secret Manager and inject via `--set-secrets` rather than as a plain env var.

After it's up, go back to the TikTok Developer Portal and add the live callback URL:

```
https://YOUR-SERVICE-URL.run.app/oauth/callback
```

### Connect from Claude

**Claude Teams (org owner adds it once for everyone):**
- Settings → Connectors → Add custom connector
- URL: `https://YOUR-SERVICE-URL.run.app/mcp`
- Each member clicks **Connect**, signs in with TikTok, done.

**claude.ai personal:**
- Settings → Connectors → Add custom connector
- URL: `https://YOUR-SERVICE-URL.run.app/mcp`

**Claude Desktop with a remote server:**
```json
{
  "mcpServers": {
    "tiktok-ads": {
      "url": "https://YOUR-SERVICE-URL.run.app/mcp"
    }
  }
}
```
Claude Desktop will run the OAuth dance the first time you use it.

---

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `TIKTOK_APP_ID` | Yes | App ID from your TikTok Business Developer app. |
| `TIKTOK_SECRET` | Yes | App secret from your TikTok Business Developer app. |
| `TIKTOK_REDIRECT_URI` | No | Override the TikTok callback URL. Defaults to `${BASE_URL}/oauth/callback`. |
| `BASE_URL` | Mode B | Public URL of this service. Used for OAuth metadata and as the canonical resource URI tokens are bound to. |
| `GCP_PROJECT_ID` | Mode B | GCP project hosting Firestore. |
| `ALLOWED_EMAILS` | No | Comma-separated allow-list of TikTok-account emails. Empty = no restriction. |
| `TIKTOK_ACCESS_TOKEN` | Mode A | Your single-user access token. Not used by the HTTP server. |
| `TIKTOK_ADVERTISER_ID` | Mode A (optional) | Default advertiser to query. |
| `TIKTOK_SANDBOX` | No | `true` to use the TikTok sandbox API base URL. Default `false`. |
| `TIKTOK_REQUEST_TIMEOUT` | No | HTTP timeout in seconds. Default `30`. |
| `PORT` | No | HTTP port (default `8080`). |

---

## Available Tools

| Tool | Description |
| --- | --- |
| `get_authorized_ad_accounts_tool` | List all advertiser accounts accessible under the current TikTok identity |
| `get_advertiser_info_tool` | Account metadata: currency, timezone, industry, status |
| `get_advertiser_balance_tool` | Current balance for the authorised advertiser |
| `get_business_centers_tool` | List Business Centers accessible to this user |
| `get_bc_assets_tool` | List assets owned by a Business Center |
| `get_bc_members_tool` | List members of a Business Center |
| `get_campaigns_tool` | List standard campaigns with optional filters |
| `get_smart_plus_campaigns_tool` | List AI-optimised Smart+ campaigns |
| `get_ad_groups_tool` | List ad groups under a campaign or advertiser |
| `get_ads_tool` | List individual ads with detailed creative and status data |
| `get_reports_tool` | Performance reports with custom dimensions, metrics, date ranges |
| `get_video_performance_tool` | TikTok video metrics: 2s/6s views, completion rate, average watch time |
| `get_video_assets_tool` | List video assets in an advertiser library |
| `get_ad_benchmark_tool` | Compare ad CTR, CVR, CPM, CPC against industry benchmarks |
| `get_creative_fatigue_tool` | Creative fatigue scores and refresh recommendations |
| `get_audience_reach_tool` | Estimated audience reach for given targeting |
| `get_targeting_options_tool` | All interest categories available for audience targeting |
| `get_pixels_tool` | List TikTok Pixel installations and tracked conversion events |
| `get_pixel_event_stats_tool` | Stats per pixel event |
| `get_offline_event_sets_tool` | List offline event sets |
| `create_async_report_tool` | Create an async report task for large datasets *(partner programme)* |
| `check_async_report_tool` | Check status of an async report task |
| `download_async_report_tool` | Download data from a completed async report |

---

## Example Prompts

```
List all my TikTok advertiser accounts

Show spend and impressions by campaign for the last 30 days

Which campaigns had the highest CPM last week?

What's the 6-second view rate for campaign 12345?

Show me Smart+ campaigns and their status

How does ad 111 CTR compare to industry benchmarks?

What interest categories can I target for a fitness audience?

List the pixel events on advertiser 67890
```

---

## OAuth endpoint reference (Mode B)

For developers who want to verify the implementation or write their own MCP client.

| Endpoint | Spec | Purpose |
| --- | --- | --- |
| `GET /.well-known/oauth-protected-resource` | RFC 9728 | Advertises the canonical resource URI and authorization server. |
| `GET /.well-known/oauth-authorization-server` | RFC 8414 | Authorization server metadata. |
| `POST /oauth/register` | RFC 7591 | Dynamic Client Registration. |
| `GET /oauth/authorize` | OAuth 2.1 | Starts the auth code flow with PKCE; redirects to TikTok. |
| `GET /oauth/callback` | — | TikTok redirects here; we mint our authorization code and bounce back to the MCP client. |
| `POST /oauth/token` | OAuth 2.1 | Authorization code + refresh token grants. |

A `GET /mcp` without a valid bearer returns `401` with a `WWW-Authenticate: Bearer resource_metadata="…"` header pointing at the protected-resource metadata document, which is how a standards-compliant MCP client discovers the rest.

> **PKCE caveat:** TikTok's OAuth implementation does not support PKCE on the upstream side, so PKCE is only enforced on the Claude → us channel. The us → TikTok channel uses a `state` parameter for CSRF protection.
>
> **Token format quirks:** TikTok's token endpoint accepts a JSON body with `app_id`, `secret`, `auth_code` (rather than the standard form-encoded `client_id` / `code`). Their access token is sent as an `Access-Token` header (rather than `Authorization: Bearer`). The OAuth proxy here normalises both into standard OAuth 2.1 for the Claude side.

---

## Tech Stack

- **Python 3.10+**
- **[FastMCP](https://github.com/modelcontextprotocol/python-sdk)** — MCP server framework
- **Starlette + uvicorn** — HTTP wrapper
- **httpx** — HTTP client for TikTok APIs
- **google-cloud-firestore** — per-user token storage and OAuth-server state (Mode B)
- **Google Cloud Run** — Serverless hosting

---

## License

MIT
