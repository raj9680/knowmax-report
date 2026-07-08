#!/usr/bin/env python3
"""
Knowmax Marketing Dashboard — HTML Builder
Reads dashboard_data.json and generates a self-contained Marketing_Dashboard.html
"""

import json
from datetime import datetime

with open("dashboard_data.json") as f:
    D = json.load(f)

INR_RATE = 84.5
generated = D.get("generated_at", datetime.now().isoformat())

# ─── Helpers ───
def fmt(n, prefix="", suffix=""):
    if n is None: return "—"
    try:
        n = float(n)
    except:
        return str(n)
    if abs(n) >= 1_000_000:
        return f"{prefix}{n/1_000_000:.1f}M{suffix}"
    if abs(n) >= 1_000:
        return f"{prefix}{n/1_000:.1f}K{suffix}"
    if n == int(n):
        return f"{prefix}{int(n)}{suffix}"
    return f"{prefix}{n:.2f}{suffix}"

def pct_change(curr, prev):
    try:
        c, p = float(curr), float(prev)
        if p == 0: return ("new", "green")
        ch = ((c - p) / p) * 100
        color = "green" if ch >= 0 else "red"
        arrow = "▲" if ch >= 0 else "▼"
        return (f"{arrow} {abs(ch):.1f}%", color)
    except:
        return ("—", "gray")

# ─── Extract data ───
ga4 = D.get("ga4", {})
gads = D.get("google_ads", {})
zoho = D.get("zoho_crm", {})
snov = D.get("snov", {})
gsc = D.get("gsc", {})
ahrefs = D.get("ahrefs", {})

traffic_cm = ga4.get("traffic", {}).get("current_month", {})
traffic_lm = ga4.get("traffic", {}).get("last_month", {})

# Build KPI cards data
kpi_cards = []

# GA4 KPIs
for key, label in [("sessions", "Sessions"), ("users", "Users"), ("pageviews", "Pageviews")]:
    val = traffic_cm.get(key, 0)
    prev = traffic_lm.get(key, 0)
    change, color = pct_change(val, prev)
    kpi_cards.append({"label": label, "value": fmt(val), "change": change, "color": color, "prev": fmt(prev), "section": "GA4"})

# Bounce rate (lower is better)
br_cm = traffic_cm.get("bounce_rate", 0)
br_lm = traffic_lm.get("bounce_rate", 0)
br_change_val = (float(br_cm) - float(br_lm)) * 100 if br_lm else 0
br_color = "green" if br_change_val <= 0 else "red"
br_arrow = "▼" if br_change_val <= 0 else "▲"
kpi_cards.append({"label": "Bounce Rate", "value": f"{float(br_cm)*100:.1f}%", "change": f"{br_arrow} {abs(br_change_val):.1f}pp", "color": br_color, "prev": f"{float(br_lm)*100:.1f}%", "section": "GA4"})

# Ahrefs KPIs
kpi_cards.append({"label": "Domain Rating", "value": str(ahrefs.get("domain_rating", "—")), "change": "", "color": "blue", "prev": "", "section": "Ahrefs"})
kpi_cards.append({"label": "Organic Keywords", "value": fmt(ahrefs.get("org_keywords", 0)), "change": f"Top 3: {ahrefs.get('org_keywords_top3', 0)}", "color": "blue", "prev": "", "section": "Ahrefs"})
kpi_cards.append({"label": "Organic Traffic", "value": fmt(ahrefs.get("org_traffic", 0)), "change": f"Value: ${fmt(ahrefs.get('org_cost', 0))}", "color": "blue", "prev": "", "section": "Ahrefs"})

# Google Ads
gads_cm = gads.get("current_month", {})
gads_lm = gads.get("last_month", {})
kpi_cards.append({"label": "Ad Spend (USD)", "value": f"${fmt(gads_cm.get('spend_usd', 0))}", "change": "", "color": "purple", "prev": f"Last: ${fmt(gads_lm.get('spend_usd', 0))}", "section": "Google Ads"})
kpi_cards.append({"label": "Ad Clicks", "value": fmt(gads_cm.get("clicks", 0)), "change": "", "color": "purple", "prev": f"Last: {fmt(gads_lm.get('clicks', 0))}", "section": "Google Ads"})

# Zoho
leads = zoho.get("leads", {})
deals = zoho.get("deals", {})
kpi_cards.append({"label": "Total Leads", "value": fmt(leads.get("total", 0)), "change": f"This month: {leads.get('this_month', 0)}", "color": "orange", "prev": "", "section": "Zoho CRM"})
kpi_cards.append({"label": "Pipeline Value", "value": f"${fmt(deals.get('pipeline_value', 0))}", "change": f"Deals: {deals.get('total', 0)}", "color": "orange", "prev": "", "section": "Zoho CRM"})
kpi_cards.append({"label": "Won Deals", "value": fmt(deals.get("won_count", 0)), "change": f"Value: ${fmt(deals.get('won_value', 0))}", "color": "orange", "prev": "", "section": "Zoho CRM"})

# Snov
snov_bal = snov.get("balance", {}).get("data", {})
kpi_cards.append({"label": "Snov Credits", "value": fmt(float(snov_bal.get("balance", 0))), "change": f"Resets in {snov_bal.get('limit_resets_in', '?')} days", "color": "teal", "prev": "", "section": "Snov.io"})

# ─── JSON for charts ───
ga4_monthly = json.dumps(ga4.get("monthly_trend", []))
ga4_channels = json.dumps(ga4.get("channels", []))
ga4_devices = json.dumps(ga4.get("devices", []))
ga4_countries = json.dumps(ga4.get("countries", [])[:20])
ga4_pages = json.dumps(ga4.get("top_pages", [])[:15])
gsc_history = json.dumps(gsc.get("performance_history", []))
gsc_keywords = json.dumps(gsc.get("top_keywords", []))
gsc_pages = json.dumps(gsc.get("top_pages", []))
gads_campaigns = json.dumps(gads.get("campaigns", []))
gads_monthly = json.dumps(gads.get("monthly_trend", []))
zoho_leads_status = json.dumps(leads.get("by_status", {}))
zoho_leads_source = json.dumps(leads.get("by_source", {}))
zoho_leads_owner = json.dumps(leads.get("by_owner", {}))
zoho_deals_stage = json.dumps(deals.get("by_stage", {}))
zoho_deals_owner = json.dumps(deals.get("by_owner", {}))


# ─── Build KPI HTML ───
def kpi_html(cards):
    html = ""
    for c in cards:
        badge_colors = {"GA4": "#4285f4", "Ahrefs": "#ff6b35", "Google Ads": "#7b2ff7", "Zoho CRM": "#e8590c", "Snov.io": "#0d9488"}
        badge_color = badge_colors.get(c["section"], "#666")
        change_html = f'<div class="kpi-change" style="color:{c["color"]}">{c["change"]}</div>' if c["change"] else ""
        prev_html = f'<div class="kpi-prev">{c["prev"]}</div>' if c["prev"] else ""
        html += f'''
        <div class="kpi-card">
            <div class="kpi-badge" style="background:{badge_color}">{c["section"]}</div>
            <div class="kpi-label">{c["label"]}</div>
            <div class="kpi-value">{c["value"]}</div>
            {change_html}
            {prev_html}
        </div>'''
    return html


# ─── Full HTML ───
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Knowmax Marketing Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {{
    --bg: #0f172a; --card: #1e293b; --card-hover: #334155; --text: #e2e8f0;
    --text-dim: #94a3b8; --accent: #38bdf8; --green: #22c55e; --red: #ef4444;
    --orange: #f59e0b; --purple: #a78bfa; --teal: #2dd4bf; --blue: #60a5fa;
    --border: #334155;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}
.header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 1px solid var(--border); padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ font-size: 1.5rem; font-weight: 700; }}
.header h1 span {{ color: var(--accent); }}
.header .meta {{ color: var(--text-dim); font-size: 0.8rem; }}
.container {{ max-width: 1600px; margin: 0 auto; padding: 24px; }}
.section-title {{ font-size: 1.1rem; font-weight: 600; margin: 28px 0 14px; color: var(--text); display: flex; align-items: center; gap: 8px; }}
.section-title .icon {{ font-size: 1.2rem; }}

/* KPI Grid */
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; margin-bottom: 24px; }}
.kpi-card {{ background: var(--card); border-radius: 12px; padding: 16px; border: 1px solid var(--border); transition: all 0.2s; position: relative; }}
.kpi-card:hover {{ background: var(--card-hover); transform: translateY(-2px); }}
.kpi-badge {{ position: absolute; top: 10px; right: 10px; font-size: 0.6rem; padding: 2px 7px; border-radius: 10px; color: white; font-weight: 600; }}
.kpi-label {{ font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
.kpi-value {{ font-size: 1.6rem; font-weight: 700; }}
.kpi-change {{ font-size: 0.8rem; margin-top: 4px; font-weight: 500; }}
.kpi-prev {{ font-size: 0.7rem; color: var(--text-dim); margin-top: 2px; }}

/* Charts Grid */
.charts-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; margin-bottom: 24px; }}
.chart-card {{ background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); }}
.chart-card.wide {{ grid-column: span 2; }}
.chart-card h3 {{ font-size: 0.9rem; color: var(--text-dim); margin-bottom: 14px; font-weight: 500; }}

/* Tables */
.data-table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
.data-table th {{ text-align: left; padding: 8px 10px; color: var(--text-dim); font-weight: 500; border-bottom: 1px solid var(--border); font-size: 0.7rem; text-transform: uppercase; }}
.data-table td {{ padding: 8px 10px; border-bottom: 1px solid rgba(51,65,85,0.5); }}
.data-table tr:hover {{ background: rgba(56,189,248,0.05); }}
.data-table .url {{ max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--accent); }}
.data-table .num {{ text-align: right; font-variant-numeric: tabular-nums; }}

/* Tabs */
.tabs {{ display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap; }}
.tab {{ padding: 6px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.8rem; color: var(--text-dim); transition: all 0.2s; }}
.tab.active {{ background: var(--accent); color: var(--bg); border-color: var(--accent); font-weight: 600; }}
.tab:hover:not(.active) {{ background: var(--card-hover); }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}

@media (max-width: 900px) {{
    .charts-grid {{ grid-template-columns: 1fr; }}
    .chart-card.wide {{ grid-column: span 1; }}
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>

<div class="header">
    <h1>📊 <span>Knowmax</span> Marketing Dashboard</h1>
    <div class="meta">Generated: {generated[:16].replace("T", " ")} | Data: GA4 · GSC · Ahrefs · Google Ads · Zoho CRM · Snov.io</div>
</div>

<div class="container">
    <!-- KPI Cards -->
    <div class="section-title"><span class="icon">📈</span> Key Metrics Overview</div>
    <div class="kpi-grid">
        {kpi_html(kpi_cards)}
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
        <div class="tab active" onclick="showSection('traffic')">Website Traffic</div>
        <div class="tab" onclick="showSection('seo')">SEO & Search</div>
        <div class="tab" onclick="showSection('ads')">Google Ads</div>
        <div class="tab" onclick="showSection('crm')">CRM Pipeline</div>
    </div>

    <!-- TRAFFIC SECTION -->
    <div class="tab-content active" id="sec-traffic">
        <div class="charts-grid">
            <div class="chart-card wide">
                <h3>Monthly Sessions & Users (Last 12 Months)</h3>
                <canvas id="chart-monthly" height="80"></canvas>
            </div>
            <div class="chart-card">
                <h3>Traffic Channels (Current Month)</h3>
                <canvas id="chart-channels" height="160"></canvas>
            </div>
            <div class="chart-card">
                <h3>Device Breakdown</h3>
                <canvas id="chart-devices" height="160"></canvas>
            </div>
            <div class="chart-card">
                <h3>Top Countries (FY 25-26)</h3>
                <div style="max-height:320px;overflow-y:auto;">
                    <table class="data-table" id="tbl-countries"></table>
                </div>
            </div>
            <div class="chart-card">
                <h3>Top Pages (Current Month)</h3>
                <div style="max-height:320px;overflow-y:auto;">
                    <table class="data-table" id="tbl-ga-pages"></table>
                </div>
            </div>
        </div>
    </div>

    <!-- SEO SECTION -->
    <div class="tab-content" id="sec-seo">
        <div class="charts-grid">
            <div class="chart-card wide">
                <h3>GSC Clicks & Impressions (Monthly, via Ahrefs)</h3>
                <canvas id="chart-gsc" height="80"></canvas>
            </div>
            <div class="chart-card">
                <h3>Top Organic Keywords (Ahrefs)</h3>
                <div style="max-height:400px;overflow-y:auto;">
                    <table class="data-table" id="tbl-keywords"></table>
                </div>
            </div>
            <div class="chart-card">
                <h3>Top Pages by Traffic (Ahrefs)</h3>
                <div style="max-height:400px;overflow-y:auto;">
                    <table class="data-table" id="tbl-seo-pages"></table>
                </div>
            </div>
        </div>
    </div>

    <!-- ADS SECTION -->
    <div class="tab-content" id="sec-ads">
        <div class="charts-grid">
            <div class="chart-card wide">
                <h3>Google Ads — Campaign Breakdown (Current Month)</h3>
                <div style="max-height:400px;overflow-y:auto;">
                    <table class="data-table" id="tbl-campaigns"></table>
                </div>
            </div>
            <div class="chart-card wide">
                <h3>Monthly Ad Spend (USD)</h3>
                <canvas id="chart-ads-monthly" height="70"></canvas>
            </div>
        </div>
    </div>

    <!-- CRM SECTION -->
    <div class="tab-content" id="sec-crm">
        <div class="charts-grid">
            <div class="chart-card">
                <h3>Leads by Status</h3>
                <canvas id="chart-leads-status" height="200"></canvas>
            </div>
            <div class="chart-card">
                <h3>Leads by Source</h3>
                <canvas id="chart-leads-source" height="200"></canvas>
            </div>
            <div class="chart-card">
                <h3>Leads by Owner</h3>
                <canvas id="chart-leads-owner" height="200"></canvas>
            </div>
            <div class="chart-card">
                <h3>Deals by Stage</h3>
                <canvas id="chart-deals-stage" height="200"></canvas>
            </div>
        </div>
    </div>
</div>

<script>
// ─── DATA ───
const ga4Monthly = {ga4_monthly};
const ga4Channels = {ga4_channels};
const ga4Devices = {ga4_devices};
const ga4Countries = {ga4_countries};
const ga4Pages = {ga4_pages};
const gscHistory = {gsc_history};
const gscKeywords = {gsc_keywords};
const gscPages = {gsc_pages};
const gadsCampaigns = {gads_campaigns};
const gadsMonthly = {gads_monthly};
const zohoLeadsStatus = {zoho_leads_status};
const zohoLeadsSource = {zoho_leads_source};
const zohoLeadsOwner = {zoho_leads_owner};
const zohoDealsStage = {zoho_deals_stage};
const zohoDealsOwner = {zoho_deals_owner};

// ─── CHART DEFAULTS ───
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(51,65,85,0.5)';
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
Chart.defaults.font.size = 11;

const palette = ['#38bdf8','#22c55e','#f59e0b','#a78bfa','#ef4444','#2dd4bf','#f472b6','#60a5fa','#fb923c','#34d399'];

// ─── Tab Navigation ───
function showSection(id) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    document.getElementById('sec-' + id).classList.add('active');
    event.target.classList.add('active');
}}

// ─── CHARTS ───

// Monthly sessions/users
new Chart(document.getElementById('chart-monthly'), {{
    type: 'line',
    data: {{
        labels: ga4Monthly.map(d => d.yearMonth),
        datasets: [
            {{ label: 'Sessions', data: ga4Monthly.map(d => parseInt(d.sessions)), borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)', fill: true, tension: 0.3 }},
            {{ label: 'Users', data: ga4Monthly.map(d => parseInt(d.users)), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', fill: true, tension: 0.3 }},
            {{ label: 'Pageviews', data: ga4Monthly.map(d => parseInt(d.pageviews)), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.3 }}
        ]
    }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ y: {{ beginAtZero: true }} }} }}
}});

// Channels
new Chart(document.getElementById('chart-channels'), {{
    type: 'doughnut',
    data: {{
        labels: ga4Channels.map(d => d.channel),
        datasets: [{{ data: ga4Channels.map(d => parseInt(d.sessions)), backgroundColor: palette }}]
    }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'right', labels: {{ font: {{ size: 10 }} }} }} }} }}
}});

// Devices
new Chart(document.getElementById('chart-devices'), {{
    type: 'doughnut',
    data: {{
        labels: ga4Devices.map(d => d.device),
        datasets: [{{ data: ga4Devices.map(d => parseInt(d.sessions)), backgroundColor: ['#38bdf8','#22c55e','#f59e0b'] }}]
    }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'right' }} }} }}
}});

// Countries table
(function() {{
    let t = '<thead><tr><th>Country</th><th class="num">Sessions</th><th class="num">Users</th></tr></thead><tbody>';
    ga4Countries.forEach(d => {{ t += `<tr><td>${{d.country}}</td><td class="num">${{Number(d.sessions).toLocaleString()}}</td><td class="num">${{Number(d.users).toLocaleString()}}</td></tr>`; }});
    t += '</tbody>';
    document.getElementById('tbl-countries').innerHTML = t;
}})();

// GA Pages table
(function() {{
    let t = '<thead><tr><th>Page</th><th class="num">Views</th><th class="num">Users</th></tr></thead><tbody>';
    ga4Pages.forEach(d => {{ t += `<tr><td class="url">${{d.page}}</td><td class="num">${{Number(d.pageviews).toLocaleString()}}</td><td class="num">${{Number(d.users).toLocaleString()}}</td></tr>`; }});
    t += '</tbody>';
    document.getElementById('tbl-ga-pages').innerHTML = t;
}})();

// GSC chart
new Chart(document.getElementById('chart-gsc'), {{
    type: 'bar',
    data: {{
        labels: gscHistory.map(d => d.date),
        datasets: [
            {{ label: 'Clicks', data: gscHistory.map(d => d.clicks), backgroundColor: 'rgba(56,189,248,0.7)', yAxisID: 'y' }},
            {{ label: 'Impressions', data: gscHistory.map(d => d.impressions), type: 'line', borderColor: '#f59e0b', backgroundColor: 'transparent', yAxisID: 'y1', tension: 0.3 }}
        ]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'top' }} }},
        scales: {{
            y: {{ beginAtZero: true, title: {{ display: true, text: 'Clicks' }} }},
            y1: {{ position: 'right', beginAtZero: true, title: {{ display: true, text: 'Impressions' }}, grid: {{ drawOnChartArea: false }} }}
        }}
    }}
}});

// Keywords table
(function() {{
    let t = '<thead><tr><th>Keyword</th><th class="num">Vol</th><th class="num">Pos</th><th class="num">Traffic</th></tr></thead><tbody>';
    gscKeywords.forEach(d => {{ t += `<tr><td>${{d.keyword}}</td><td class="num">${{Number(d.volume).toLocaleString()}}</td><td class="num">${{d.position}}</td><td class="num">${{d.traffic}}</td></tr>`; }});
    t += '</tbody>';
    document.getElementById('tbl-keywords').innerHTML = t;
}})();

// SEO Pages table
(function() {{
    let t = '<thead><tr><th>URL</th><th class="num">Traffic</th><th class="num">KWs</th><th>Top Keyword</th></tr></thead><tbody>';
    gscPages.forEach(d => {{
        const short = d.url.replace('https://knowmax.ai','');
        t += `<tr><td class="url" title="${{d.url}}">${{short}}</td><td class="num">${{d.traffic}}</td><td class="num">${{d.keywords}}</td><td>${{d.top_keyword}}</td></tr>`;
    }});
    t += '</tbody>';
    document.getElementById('tbl-seo-pages').innerHTML = t;
}})();

// Campaigns table
(function() {{
    let t = '<thead><tr><th>Campaign</th><th>Status</th><th class="num">Spend (USD)</th><th class="num">Clicks</th><th class="num">Impr</th><th class="num">Conv</th></tr></thead><tbody>';
    gadsCampaigns.forEach(d => {{
        const statusColor = d.status === 'ENABLED' ? '#22c55e' : '#94a3b8';
        t += `<tr><td>${{d.name}}</td><td style="color:${{statusColor}}">${{d.status}}</td><td class="num">${{d.spend_usd}}</td><td class="num">${{d.clicks}}</td><td class="num">${{Number(d.impressions).toLocaleString()}}</td><td class="num">${{d.conversions}}</td></tr>`;
    }});
    t += '</tbody>';
    document.getElementById('tbl-campaigns').innerHTML = t;
}})();

// Ads monthly spend
if (gadsMonthly.length > 0) {{
    new Chart(document.getElementById('chart-ads-monthly'), {{
        type: 'bar',
        data: {{
            labels: gadsMonthly.map(d => d.month),
            datasets: [{{ label: 'Spend (USD)', data: gadsMonthly.map(d => d.spend_usd), backgroundColor: 'rgba(167,139,250,0.7)' }}]
        }},
        options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
}}

// CRM Charts
function barChart(id, dataObj, color) {{
    const labels = Object.keys(dataObj);
    const values = Object.values(dataObj);
    new Chart(document.getElementById(id), {{
        type: 'bar',
        data: {{
            labels: labels,
            datasets: [{{ data: values.map(v => parseInt(v)), backgroundColor: color, borderRadius: 4 }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{ x: {{ beginAtZero: true }} }}
        }}
    }});
}}

barChart('chart-leads-status', zohoLeadsStatus, 'rgba(56,189,248,0.7)');
barChart('chart-leads-source', zohoLeadsSource, 'rgba(34,197,94,0.7)');
barChart('chart-leads-owner', zohoLeadsOwner, 'rgba(245,158,11,0.7)');
barChart('chart-deals-stage', zohoDealsStage, 'rgba(167,139,250,0.7)');

</script>
</body>
</html>'''

# Write output
output_path = "Marketing_Dashboard.html"
with open(output_path, "w") as f:
    f.write(html)

print(f"✅ Dashboard written to {output_path}")
print(f"   KPI cards: {len(kpi_cards)}")
print(f"   Sections: Traffic, SEO & Search, Google Ads, CRM Pipeline")
