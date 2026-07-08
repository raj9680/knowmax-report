#!/usr/bin/env python3
"""
Knowmax Marketing Dashboard — Data Fetcher
Pulls from GA4, Google Ads, Zoho CRM, Snov.io
GSC data is injected separately via Ahrefs MCP.
Writes dashboard_data.json.
"""

import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests
import yaml

# ─── CONFIG ───────────────────────────────────────────────────────────
GA4_PROPERTY_ID = "251430515"
GOOGLE_ADS_CUSTOMER_ID = "7735901637"
INR_USD_RATE = 84.5

ZOHO_OWNERS = [
    "Pratik Salia", "Arjun Mattu", "Alan Palacios", "Team Knowmax",
    "Amol Rastogi", "Ronak Gupta", "Yatharth Jain", "Rahul Dhanak", "Rishu Kapoor"
]

# Date ranges
today = datetime.now()
# Current month
cm_start = today.replace(day=1).strftime("%Y-%m-%d")
cm_end = today.strftime("%Y-%m-%d")

# Last month
lm_end = (today.replace(day=1) - timedelta(days=1))
lm_start = lm_end.replace(day=1).strftime("%Y-%m-%d")
lm_end_str = lm_end.strftime("%Y-%m-%d")

# FY 25-26: Apr 2025 – Mar 2026
fy_start = "2025-04-01"
fy_end = "2026-03-31"

# Last 12 months for trends
twelve_months_ago = (today - relativedelta(months=12)).strftime("%Y-%m-%d")

data = {
    "generated_at": today.isoformat(),
    "ga4": {},
    "google_ads": {},
    "zoho_crm": {},
    "snov": {},
    "gsc": {},       # filled by Ahrefs MCP
    "ahrefs": {},    # filled by Ahrefs MCP
}


# ═══════════════════════════════════════════════════════════════════════
# 1. GA4
# ═══════════════════════════════════════════════════════════════════════
def fetch_ga4():
    print("📊 Fetching GA4 data...")
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Dimension, Metric, OrderBy, FilterExpression, Filter
        )
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            "creds.json",
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        prop = f"properties/{GA4_PROPERTY_ID}"

        # ── Helper ──
        def run_report(date_ranges, dimensions, metrics, limit=10000, order_by=None):
            req = RunReportRequest(
                property=prop,
                date_ranges=date_ranges,
                dimensions=dimensions,
                metrics=metrics,
                limit=limit,
            )
            if order_by:
                req.order_bys = order_by
            return client.run_report(req)

        def parse_rows(resp, dim_names, met_names):
            rows = []
            for row in resp.rows:
                r = {}
                for i, d in enumerate(dim_names):
                    r[d] = row.dimension_values[i].value
                for i, m in enumerate(met_names):
                    r[m] = row.metric_values[i].value
                rows.append(r)
            return rows

        # ── Overall traffic (current month vs last month — separate queries) ──
        traffic_metrics = [
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
            Metric(name="engagedSessions"),
        ]
        traffic = {}
        for period, ds, de in [("current_month", cm_start, cm_end), ("last_month", lm_start, lm_end_str)]:
            resp = run_report(
                date_ranges=[DateRange(start_date=ds, end_date=de)],
                dimensions=[],
                metrics=traffic_metrics,
            )
            if resp.rows:
                row = resp.rows[0]
                traffic[period] = {
                    "sessions": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                    "new_users": int(row.metric_values[2].value),
                    "pageviews": int(row.metric_values[3].value),
                    "avg_session_duration": float(row.metric_values[4].value),
                    "bounce_rate": float(row.metric_values[5].value),
                    "engaged_sessions": int(row.metric_values[6].value),
                }
        data["ga4"]["traffic"] = traffic

        # ── Monthly trend (last 12 months) ──
        resp = run_report(
            date_ranges=[DateRange(start_date=twelve_months_ago, end_date=cm_end)],
            dimensions=[Dimension(name="yearMonth")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
            ],
            order_by=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="yearMonth"))],
        )
        data["ga4"]["monthly_trend"] = parse_rows(resp, ["yearMonth"], ["sessions", "users", "pageviews"])

        # ── Channels ──
        resp = run_report(
            date_ranges=[DateRange(start_date=cm_start, end_date=cm_end)],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[Metric(name="sessions"), Metric(name="totalUsers"), Metric(name="conversions")],
            order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        )
        data["ga4"]["channels"] = parse_rows(resp, ["channel"], ["sessions", "users", "conversions"])

        # ── Top pages ──
        resp = run_report(
            date_ranges=[DateRange(start_date=cm_start, end_date=cm_end)],
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="screenPageViews"), Metric(name="totalUsers"), Metric(name="averageSessionDuration")],
            limit=20,
            order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        )
        data["ga4"]["top_pages"] = parse_rows(resp, ["page"], ["pageviews", "users", "avg_duration"])

        # ── Devices ──
        resp = run_report(
            date_ranges=[DateRange(start_date=cm_start, end_date=cm_end)],
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        )
        data["ga4"]["devices"] = parse_rows(resp, ["device"], ["sessions", "users"])

        # ── Countries (FY scope, split into 2 queries to avoid 2000 row limit) ──
        countries = []
        for ds, de in [("2025-04-01", "2025-09-30"), ("2025-10-01", "2026-03-31")]:
            resp = run_report(
                date_ranges=[DateRange(start_date=ds, end_date=de)],
                dimensions=[Dimension(name="country")],
                metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
                limit=2000,
                order_by=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
            )
            for row in resp.rows:
                countries.append({
                    "country": row.dimension_values[0].value,
                    "sessions": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                })
        # Aggregate by country
        from collections import defaultdict
        agg = defaultdict(lambda: {"sessions": 0, "users": 0})
        for c in countries:
            agg[c["country"]]["sessions"] += c["sessions"]
            agg[c["country"]]["users"] += c["users"]
        data["ga4"]["countries"] = sorted(
            [{"country": k, **v} for k, v in agg.items()],
            key=lambda x: x["sessions"], reverse=True
        )[:30]

        print("  ✅ GA4 done")
    except Exception as e:
        print(f"  ❌ GA4 error: {e}")
        traceback.print_exc()
        data["ga4"]["error"] = str(e)


# ═══════════════════════════════════════════════════════════════════════
# 2. GOOGLE ADS
# ═══════════════════════════════════════════════════════════════════════
def fetch_google_ads():
    print("💰 Fetching Google Ads data...")
    try:
        from google.ads.googleads.client import GoogleAdsClient

        gads_client = GoogleAdsClient.load_from_storage("google-ads.yaml")
        ga_service = gads_client.get_service("GoogleAdsService")

        # ── Account-level spend (current month) ──
        query_cm = f"""
            SELECT
                metrics.cost_micros,
                metrics.clicks,
                metrics.impressions,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM customer
            WHERE segments.date BETWEEN '{cm_start}' AND '{cm_end}'
        """
        resp = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query_cm)
        cm_data = {"spend_inr": 0, "spend_usd": 0, "clicks": 0, "impressions": 0, "conversions": 0}
        for row in resp:
            cm_data["spend_inr"] += row.metrics.cost_micros / 1e6
            cm_data["clicks"] += row.metrics.clicks
            cm_data["impressions"] += row.metrics.impressions
            cm_data["conversions"] += row.metrics.conversions
        cm_data["spend_usd"] = round(cm_data["spend_inr"] / INR_USD_RATE, 2)
        cm_data["spend_inr"] = round(cm_data["spend_inr"], 2)
        if cm_data["clicks"] > 0:
            cm_data["cpc_usd"] = round(cm_data["spend_usd"] / cm_data["clicks"], 2)
        if cm_data["impressions"] > 0:
            cm_data["ctr"] = round(cm_data["clicks"] / cm_data["impressions"] * 100, 2)
        data["google_ads"]["current_month"] = cm_data

        # ── Last month ──
        query_lm = f"""
            SELECT
                metrics.cost_micros,
                metrics.clicks,
                metrics.impressions,
                metrics.conversions
            FROM customer
            WHERE segments.date BETWEEN '{lm_start}' AND '{lm_end_str}'
        """
        resp = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query_lm)
        lm_data = {"spend_inr": 0, "spend_usd": 0, "clicks": 0, "impressions": 0, "conversions": 0}
        for row in resp:
            lm_data["spend_inr"] += row.metrics.cost_micros / 1e6
            lm_data["clicks"] += row.metrics.clicks
            lm_data["impressions"] += row.metrics.impressions
            lm_data["conversions"] += row.metrics.conversions
        lm_data["spend_usd"] = round(lm_data["spend_inr"] / INR_USD_RATE, 2)
        lm_data["spend_inr"] = round(lm_data["spend_inr"], 2)
        data["google_ads"]["last_month"] = lm_data

        # ── Monthly trend ──
        query_monthly = f"""
            SELECT
                segments.month,
                metrics.cost_micros,
                metrics.clicks,
                metrics.impressions,
                metrics.conversions
            FROM customer
            WHERE segments.date BETWEEN '{twelve_months_ago}' AND '{cm_end}'
        """
        resp = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query_monthly)
        monthly = {}
        for row in resp:
            m = row.segments.month  # YYYY-MM
            if m not in monthly:
                monthly[m] = {"spend_inr": 0, "clicks": 0, "impressions": 0, "conversions": 0}
            monthly[m]["spend_inr"] += row.metrics.cost_micros / 1e6
            monthly[m]["clicks"] += row.metrics.clicks
            monthly[m]["impressions"] += row.metrics.impressions
            monthly[m]["conversions"] += row.metrics.conversions
        trend = []
        for m in sorted(monthly.keys()):
            d = monthly[m]
            d["month"] = m
            d["spend_usd"] = round(d["spend_inr"] / INR_USD_RATE, 2)
            d["spend_inr"] = round(d["spend_inr"], 2)
            trend.append(d)
        data["google_ads"]["monthly_trend"] = trend

        # ── Campaign breakdown (current month) ──
        query_campaigns = f"""
            SELECT
                campaign.name,
                campaign.status,
                metrics.cost_micros,
                metrics.clicks,
                metrics.impressions,
                metrics.conversions,
                metrics.ctr
            FROM campaign
            WHERE segments.date BETWEEN '{cm_start}' AND '{cm_end}'
                AND campaign.status != 'REMOVED'
            ORDER BY metrics.cost_micros DESC
            LIMIT 20
        """
        resp = ga_service.search(customer_id=GOOGLE_ADS_CUSTOMER_ID, query=query_campaigns)
        campaigns = []
        for row in resp:
            spend_inr = row.metrics.cost_micros / 1e6
            campaigns.append({
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "spend_inr": round(spend_inr, 2),
                "spend_usd": round(spend_inr / INR_USD_RATE, 2),
                "clicks": row.metrics.clicks,
                "impressions": row.metrics.impressions,
                "conversions": round(row.metrics.conversions, 1),
                "ctr": round(row.metrics.ctr * 100, 2),
            })
        data["google_ads"]["campaigns"] = campaigns

        print("  ✅ Google Ads done")
    except Exception as e:
        print(f"  ❌ Google Ads error: {e}")
        traceback.print_exc()
        data["google_ads"]["error"] = str(e)


# ═══════════════════════════════════════════════════════════════════════
# 3. ZOHO CRM
# ═══════════════════════════════════════════════════════════════════════
def fetch_zoho_crm():
    print("📋 Fetching Zoho CRM data...")
    try:
        with open("zoho_tokens.json") as f:
            tokens = json.load(f)

        # Refresh access token
        resp = requests.post(tokens["auth_url"], params={
            "grant_type": "refresh_token",
            "client_id": tokens["client_id"],
            "client_secret": tokens["client_secret"],
            "refresh_token": tokens["refresh_token"],
        })
        resp.raise_for_status()
        access_token = resp.json()["access_token"]
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        api = tokens["api_domain"]

        # ── Fetch leads ──
        leads_all = []
        page = 1
        while True:
            r = requests.get(
                f"{api}/crm/v2/Leads",
                headers=headers,
                params={"per_page": 200, "page": page, "fields": "Owner,Lead_Status,Created_Time,Lead_Source"}
            )
            if r.status_code != 200:
                break
            body = r.json()
            if "data" not in body:
                break
            for lead in body["data"]:
                owner_name = lead.get("Owner", {}).get("name", "")
                if owner_name in ZOHO_OWNERS:
                    leads_all.append({
                        "owner": owner_name,
                        "status": lead.get("Lead_Status", "Unknown"),
                        "created": lead.get("Created_Time", ""),
                        "source": lead.get("Lead_Source", "Unknown"),
                    })
            if not body.get("info", {}).get("more_records", False):
                break
            page += 1

        # Summarize leads
        from collections import Counter
        lead_status_counts = Counter(l["status"] for l in leads_all)
        lead_source_counts = Counter(l["source"] for l in leads_all)
        lead_owner_counts = Counter(l["owner"] for l in leads_all)

        # Leads created this month
        leads_this_month = [l for l in leads_all if l["created"][:7] == today.strftime("%Y-%m")]

        data["zoho_crm"]["leads"] = {
            "total": len(leads_all),
            "this_month": len(leads_this_month),
            "by_status": dict(lead_status_counts.most_common(15)),
            "by_source": dict(lead_source_counts.most_common(15)),
            "by_owner": dict(lead_owner_counts),
        }

        # ── Fetch deals ──
        deals_all = []
        page = 1
        while True:
            r = requests.get(
                f"{api}/crm/v2/Deals",
                headers=headers,
                params={"per_page": 200, "page": page, "fields": "Owner,Stage,Amount,Closing_Date,Created_Time,Deal_Name"}
            )
            if r.status_code != 200:
                break
            body = r.json()
            if "data" not in body:
                break
            for deal in body["data"]:
                owner_name = deal.get("Owner", {}).get("name", "")
                if owner_name in ZOHO_OWNERS:
                    deals_all.append({
                        "owner": owner_name,
                        "stage": deal.get("Stage", "Unknown"),
                        "amount": deal.get("Amount") or 0,
                        "closing_date": deal.get("Closing_Date", ""),
                        "created": deal.get("Created_Time", ""),
                        "name": deal.get("Deal_Name", ""),
                    })
            if not body.get("info", {}).get("more_records", False):
                break
            page += 1

        # Summarize deals
        deal_stage_counts = Counter(d["stage"] for d in deals_all)
        pipeline_value = sum(d["amount"] for d in deals_all if d["stage"] not in ["Closed Lost", "Closed-Lost"])
        won_deals = [d for d in deals_all if d["stage"] in ["Closed Won", "Closed-Won"]]
        won_value = sum(d["amount"] for d in won_deals)

        data["zoho_crm"]["deals"] = {
            "total": len(deals_all),
            "pipeline_value": pipeline_value,
            "won_count": len(won_deals),
            "won_value": won_value,
            "by_stage": dict(deal_stage_counts.most_common(15)),
            "by_owner": dict(Counter(d["owner"] for d in deals_all)),
        }

        print(f"  ✅ Zoho CRM done — {len(leads_all)} leads, {len(deals_all)} deals")
    except Exception as e:
        print(f"  ❌ Zoho CRM error: {e}")
        traceback.print_exc()
        data["zoho_crm"]["error"] = str(e)


# ═══════════════════════════════════════════════════════════════════════
# 4. SNOV.IO
# ═══════════════════════════════════════════════════════════════════════
def fetch_snov():
    print("📧 Fetching Snov.io data...")
    try:
        with open("snov_tokens.json") as f:
            tokens = json.load(f)

        # Refresh access token
        resp = requests.post("https://api.snov.io/v1/oauth/access_token", json={
            "grant_type": "client_credentials",
            "client_id": tokens["client_id"],
            "client_secret": tokens["client_secret"],
        })
        resp.raise_for_status()
        access_token = resp.json()["access_token"]

        # Get user balance/credits
        resp = requests.get(
            "https://api.snov.io/v1/get-balance",
            params={"access_token": access_token}
        )
        if resp.status_code == 200:
            balance = resp.json()
            data["snov"]["balance"] = balance
        else:
            data["snov"]["balance"] = {"error": f"HTTP {resp.status_code}"}

        # Get prospect lists count
        resp = requests.get(
            "https://api.snov.io/v1/get-user-lists",
            params={"access_token": access_token}
        )
        if resp.status_code == 200:
            lists = resp.json()
            data["snov"]["lists_count"] = len(lists) if isinstance(lists, list) else 0

        print("  ✅ Snov.io done")
    except Exception as e:
        print(f"  ❌ Snov.io error: {e}")
        traceback.print_exc()
        data["snov"]["error"] = str(e)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  Knowmax Marketing Dashboard — Data Fetcher")
    print(f"  Date: {today.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    fetch_ga4()
    fetch_google_ads()
    fetch_zoho_crm()
    fetch_snov()

    # Write output
    with open("dashboard_data.json", "w") as f:
        json.dump(data, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("  ✅ dashboard_data.json written")
    print("  ⚠️  GSC + Ahrefs data must be injected separately via MCP")
    print("=" * 60)
