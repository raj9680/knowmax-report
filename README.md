# Knowmax Marketing Dashboard

A self-contained marketing analytics dashboard that pulls live data from 6 sources and generates an offline HTML report.

## Data Sources

| Source | Data |
|---|---|
| **GA4** | Website traffic, channels, devices, countries |
| **GSC** | Search clicks, impressions, CTR, keywords, pages (via Ahrefs MCP) |
| **Google Ads** | Spend, campaigns (INR→USD converted) |
| **Zoho CRM** | Pipeline, leads, deals (filtered by Knowmax SBU owners) |
| **Snov.io** | Cold outreach credits |
| **Ahrefs** | Domain rating, backlinks, organic keywords |

## Setup

### 1. Install Dependencies

```bash
pip install google-ads==30.0.0 google-analytics-data==0.20.0 google-auth==2.49.1 requests python-dateutil pyyaml --break-system-packages
```

### 2. Create Credential Files

See `DASHBOARD_SETUP_INSTRUCTIONS.md` for full credential details. You need:

- `creds.json` — GA4 service account key
- `google-ads.yaml` — Google Ads OAuth2 config
- `zoho_tokens.json` — Zoho CRM tokens
- `zoho_campaigns_tokens.json` — Zoho Campaigns tokens
- `snov_tokens.json` — Snov.io tokens

> **Warning:** Never commit credential files to git.

### 3. Run

```bash
# Fetch live data from all APIs
python3 fetch_data.py

# Build the dashboard HTML
python3 build_dashboard.py
```

### 4. View

Open `Marketing_Dashboard.html` in any browser. No server needed — all data is embedded.

## File Structure

```
├── .gitignore
├── README.md
├── DASHBOARD_SETUP_INSTRUCTIONS.md
├── fetch_data.py                  ← Pulls from GA4, Google Ads, Zoho, Snov → dashboard_data.json
├── build_dashboard.py             ← Reads dashboard_data.json → Marketing_Dashboard.html
├── Marketing_Dashboard.html       ← Final dashboard (open in browser)
└── dashboard_data.json            ← Generated (not committed)
```

## Key Notes

- **Google Ads currency is INR** — costs are auto-converted to USD at rate 84.5
- **GSC uses Ahrefs MCP** — the service account doesn't have direct GSC access
- **Zoho CRM is filtered** by 9 Knowmax/Kocharsoft SBU owners
- **Dashboard is fully offline** — no API calls at runtime

---

*Knowmax Marketing Dashboard v2.0*
