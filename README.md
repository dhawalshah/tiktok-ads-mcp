# TikTok Ads MCP

A comprehensive Model Context Protocol (MCP) server for interacting with the TikTok Business API. Query campaigns, video performance, audience targeting, benchmarks, and more directly from Claude or any MCP-compatible client.

## Features

- **Read-Only TikTok Business API Integration**: Access all major TikTok advertising endpoints for data retrieval
- **14 Tools**: Covers accounts, campaigns, Smart+ campaigns, ad groups, ads, reports, video performance, ad benchmarks, targeting options, pixels, creative fatigue, and async reports
- **Advanced Filtering**: Powerful filtering options for all data retrieval operations
- **Multi-Advertiser Support**: Handle multiple advertiser accounts in a single request
- **Flexible Reporting**: Generate detailed performance reports with custom dimensions and metrics
- **Cloud Run Ready**: Deploy a shared team instance with a single script
- **Error Handling**: Comprehensive error handling and validation
- **Modular Architecture**: Clean, maintainable code structure
- **Safe Operations**: All tools are read-only and will not modify your campaigns or ad data

## Available Tools

| Tool | Description | Status |
|------|-------------|--------|
| `get_authorized_ad_accounts_tool` | List all advertiser accounts under your access token | ✅ |
| `get_advertiser_info_tool` | Account metadata: currency, timezone, industry, status | ✅ |
| `get_business_centers_tool` | List accessible business centers | ✅ |
| `get_campaigns_tool` | List standard campaigns with optional filters | ✅ |
| `get_smart_plus_campaigns_tool` | List AI-optimised Smart+ campaigns (separate API) | ✅ |
| `get_ad_groups_tool` | List ad groups under a campaign or advertiser | ✅ |
| `get_ads_tool` | List individual ads with detailed creative data | ✅ |
| `get_reports_tool` | Performance reports with custom dimensions, metrics, and date ranges | ✅ |
| `get_video_performance_tool` | TikTok-specific video metrics: 2s/6s views, completion rate, watch time | ✅ |
| `get_ad_benchmark_tool` | Compare ad CTR/CVR/CPM/CPC against industry benchmarks | ✅ |
| `get_targeting_options_tool` | Browse interest categories available for audience targeting | ✅ |
| `get_pixels_tool` | List TikTok Pixel installations and tracked conversion events | ✅ |
| `get_creative_fatigue_tool` | Creative fatigue scores and refresh recommendations | ⚠️ Requires TikTok partner access |
| `create/check/download_async_report_tool` | Async report pipeline for large datasets | ⚠️ Requires TikTok partner access |

## Prerequisites

- Python 3.10 or higher
- TikTok Business API access
- Valid API credentials (app ID, secret, access token)

## Quick Start

### Installation

1. **Download the TikTok Ads MCP**
   - Click the green "Code" button at the top of the GitHub page
   - Select "Download ZIP"
   - Unzip the downloaded file to a location you can easily find (like your Documents folder)

2. **Alternatively, if you're familiar with Git:**
   ```bash
   git clone https://github.com/dhawalshah/tiktok-ads-mcp.git
   ```

3. **Install Dependencies**
   ```bash
   cd tiktok-ads-mcp
   pip install -e .
   ```


### Configuration

1. **Set up environment variables** in your MCP client configuration:

```json
{
  "mcpServers": {
    "tiktok-ads": {
      "command": "python",
      "args": ["-m", "tiktok_ads_mcp"],
      "env": {
        "TIKTOK_APP_ID": "your_app_id",
        "TIKTOK_SECRET": "your_secret",
        "TIKTOK_ACCESS_TOKEN": "your_access_token"
      }
    }
  }
}
```

2. **Required credentials**:
   - `TIKTOK_APP_ID`: Your TikTok app ID
   - `TIKTOK_SECRET`: Your TikTok app secret
   - `TIKTOK_ACCESS_TOKEN`: Your access token

   **How to get these credentials:**
   1. Go to the [TikTok for Business Developers](https://ads.tiktok.com/marketing_api/) portal and log in.
   2. Click "My Apps" and create a new app.
   3. Select "Marketing API" as the service type.
   4. In the app settings, enable permissions related to **Reading** and **Reporting** (e.g., `Ads Management`, `Reporting`).
   5. Once approved, you will find your `App ID` and `Secret` in the app details.
   6. Generate an `Access Token` using the "TikTok Marketing API Inspector" or via the OAuth flow documented in the portal.

### Usage

Once configured, you can use the MCP tools through your MCP client (like Cursor, Claude Desktop, etc.):

- **Get business centers and advertiser accounts** to discover available accounts
- **Retrieve campaigns** with filtering by status, objective, or date range
- **Access ad groups** with advanced targeting and optimization settings
- **View ads** with detailed creative and performance data
- **Generate reports** with custom dimensions, metrics, and time ranges
- **Access real-time advertising data** and performance metrics

## Cloud Run Deployment (Team / Self-Hosted)

Deploy a shared instance for your team on Google Cloud Run.

### Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI authenticated (`gcloud auth login`)
- Docker installed locally
- Artifact Registry repository created:
  ```bash
  gcloud artifacts repositories create mcp-servers \
    --repository-format=docker \
    --location=asia-southeast1 \
    --project=YOUR_PROJECT_ID
  ```

### Deploy

```bash
# Set your TikTok credentials
export TIKTOK_APP_ID=your_app_id
export TIKTOK_SECRET=your_app_secret
export TIKTOK_ACCESS_TOKEN=your_access_token

# Optional: protect the endpoint with a shared team key
# export MCP_API_KEY=your_team_secret

# Deploy (builds, pushes, and deploys in one step)
gcloud config set project YOUR_PROJECT_ID
./deploy.sh
```

After deployment, set your secrets permanently in Cloud Run:
```bash
gcloud run services update tiktok-ads-mcp \
  --region=asia-southeast1 \
  --update-env-vars="TIKTOK_APP_ID=...,TIKTOK_SECRET=...,TIKTOK_ACCESS_TOKEN=..."
```

### Connect Claude

Add to your Claude Desktop `claude_desktop_config.json` or team connector:

```json
{
  "mcpServers": {
    "tiktok-ads": {
      "url": "https://YOUR_SERVICE_URL/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_API_KEY"
      }
    }
  }
}
```

Omit the `headers` block if `MCP_API_KEY` is not set.

### Health Check

```bash
curl https://YOUR_SERVICE_URL/health
# {"status":"healthy","service":"tiktok-ads-mcp","transport":"streamable-http","auth":"enabled"}
```

### Automated Deployments (Cloud Build)

Connect `cloudbuild.yaml` to a GitHub trigger in the GCP console to deploy automatically on push to `main`.

## API Coverage

This MCP server provides **read-only** access to the TikTok Business API:

### Business Management
- Business center retrieval and access
- Advertiser account information and permissions

### Campaign Management
- Campaign retrieval and filtering
- Campaign status and performance monitoring
- Campaign budget and objective information

### Ad Group Management
- Ad group retrieval and filtering
- Advanced targeting and optimization settings
- Performance monitoring and analysis

### Ad Management
- Ad retrieval and filtering
- Creative asset information
- Performance tracking and analysis

### Reporting & Analytics
- Basic performance reports
- Audience insights reports
- Playable ads reports
- DSA (Dynamic Search Ads) reports
- Business Center reports
- GMV max ads reports

## Key Features

### Advanced Filtering
All tools support comprehensive filtering options:
- Status-based filtering (active, paused, deleted)
- Time-based filtering (creation date, modification date)
- Performance-based filtering (budget, optimization goals)
- Creative filtering (ad formats, material types)

### Modern Implementation
This package uses the official FastMCP framework for optimal performance and developer experience:

- **Automatic Schema Generation**: From Python type hints
- **Simplified Tool Registration**: Using `@app.tool()` decorators
- **Built-in Error Handling**: Consistent error responses
- **Type Safety**: Full parameter validation from type hints
- **Future-Proof**: Part of the official MCP SDK

### Multi-Advertiser Support
- Handle multiple advertiser accounts in single requests
- Cross-advertiser reporting and analytics
- Unified data access across accounts

### Flexible Reporting
- Custom dimensions and metrics
- Multiple report types and data levels
- Time-based and lifetime metrics
- Aggregated and detailed views

### Error Handling
- Comprehensive parameter validation
- Detailed error messages and suggestions
- Graceful handling of API limitations
- Rate limiting and retry logic

## Documentation

- **MCP_USAGE.md**: Comprehensive usage guide with examples
- **TikTok Business API**: Official API documentation
- **Project Wiki**: Additional resources and guides

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests and documentation
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the [MCP_USAGE.md](MCP_USAGE.md) documentation
2. Review the [TikTok Business API documentation](https://developers.tiktok.com/doc/tiktok-business-api)
3. Open an issue on the GitHub repository
4. Contact the development team

## Changelog

### v0.2.0 (Current)
- **14 Tools**: Added `get_video_performance`, `get_ad_benchmark`, `get_targeting_options`, `get_smart_plus_campaigns`, `get_pixels`, `get_advertiser_info`, `get_creative_fatigue`, and async report pipeline
- **Cloud Run Deployment**: Streamable HTTP transport via `server_http.py`; `deploy.sh` one-shot deploy script
- **Real API Validation**: All tools smoke-tested against live TikTok Business API

### v0.1.3
- **Async Support**: Complete refactor to use `async/await` with `httpx` for improved performance
- **Retry Logic**: Added automatic retries for rate limits and server errors using `tenacity`
- **Error Handling**: Simplified and standardized error handling with decorators
- **Dependencies**: Switched from `requests` to `httpx`

### v0.1.2
- **FastMCP Implementation**: Modern MCP server using official FastMCP framework
- **Automatic Schema Generation**: From Python type hints
- **Simplified Tool Registration**: Using `@app.tool()` decorators

### v0.1.1
- Complete implementation of original 6 tools
- Multi-advertiser support and advanced filtering
- Modular tools architecture

### v0.1.0
- Initial release with basic MCP server structure
- Core API client implementation