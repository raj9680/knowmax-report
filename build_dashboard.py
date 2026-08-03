import json, datetime

ga = json.load(open("ga4_data.json"))
ads = json.load(open("ads_data.json"))
crm = json.load(open("crm_data.json"))
seo = json.load(open("seo_data.json"))

TODAY = datetime.date(2026, 8, 3)
gen = TODAY.strftime("%d %b %Y")

cur = ga["current_month"][0]
lastfull = ga["last_month"][0]
lastsp = ga["last_month_same_period"][0]

def pct(a, b):
    if not b:
        return None
    return (a - b) / b * 100.0

# Open pipeline = all stages not starting with "Closed"
open_stages = [s for s in crm["deals_by_stage"] if not s["stage"].lower().startswith("closed")]
open_pipeline = sum(s["value"] for s in open_stages)
open_count = sum(s["count"] for s in open_stages)

snov_bal = 0
try:
    snov_bal = float(crm["snov"]["data"]["balance"])
except Exception:
    pass

ads_last = ads["last_month"]
ads_ytd = sum(m["cost_usd"] for m in ads["monthly"])
ads_clicks_ytd = sum(m["clicks"] for m in ads["monthly"])

gsc_last = seo["gsc_monthly"][-1]

KPIS = [
    {"label": "Sessions", "value": f'{int(cur["sessions"]):,}', "sub": "Aug 2026 MTD",
     "delta": pct(cur["sessions"], lastsp["sessions"]), "note": "vs Jul 1–3", "group": "traffic"},
    {"label": "Users", "value": f'{int(cur["totalUsers"]):,}', "sub": "Aug 2026 MTD",
     "delta": pct(cur["totalUsers"], lastsp["totalUsers"]), "note": "vs Jul 1–3", "group": "traffic"},
    {"label": "Pageviews", "value": f'{int(cur["screenPageViews"]):,}', "sub": "Aug 2026 MTD",
     "delta": pct(cur["screenPageViews"], lastsp["screenPageViews"]), "note": "vs Jul 1–3", "group": "traffic"},
    {"label": "Bounce Rate", "value": f'{cur["bounceRate"]*100:.1f}%', "sub": "Aug 2026 MTD",
     "delta": pct(cur["bounceRate"], lastsp["bounceRate"]), "note": "vs Jul 1–3",
     "group": "traffic", "invert": True},
    {"label": "Domain Rating", "value": f'{seo["domain_rating"]:.0f}', "sub": f'Ahrefs rank {seo["ahrefs_rank"]:,}',
     "group": "seo"},
    {"label": "Organic Keywords", "value": f'{seo["org_keywords"]:,}',
     "sub": f'{seo["org_keywords_1_3"]:,} in top 3', "group": "seo"},
    {"label": "Organic Traffic", "value": f'{seo["org_traffic"]:,}',
     "sub": f'≈ ${seo["org_traffic_value_usd"]:,.0f}/mo value', "group": "seo"},
    {"label": "Ad Spend", "value": f'${ads_last["cost_usd"]:,.0f}', "sub": "Jul 2026 · $%s trailing 12m" % f"{ads_ytd:,.0f}",
     "group": "ads"},
    {"label": "Ad Clicks", "value": f'{ads_last["clicks"]:,}', "sub": f'{ads_clicks_ytd:,} trailing 12m',
     "group": "ads"},
    {"label": "Total Leads", "value": f'{crm["leads_total"]:,}', "sub": "9 tracked owners", "group": "crm"},
    {"label": "Open Pipeline", "value": f'{open_pipeline/1e6:,.2f}M', "sub": f'{open_count} open deals',
     "group": "crm"},
    {"label": "Won Deals", "value": f'{crm["won_count"]}', "sub": f'{crm["won_value"]/1e3:,.0f}K won value',
     "group": "crm"},
    {"label": "Snov Credits", "value": f'{snov_bal:,.0f}', "sub": "balance remaining", "group": "ops"},
]

DATA = {
    "generated": gen,
    "ga": ga, "ads": ads, "crm": crm, "seo": seo,
    "open_pipeline": open_pipeline, "open_count": open_count,
    "gsc_last": gsc_last,
}

def kpi_html(k):
    d = k.get("delta")
    if d is None:
        badge = ""
    else:
        good = d < 0 if k.get("invert") else d > 0
        cls = "up" if good else ("flat" if abs(d) < 0.05 else "down")
        arrow = "▲" if d > 0 else ("▼" if d < 0 else "■")
        badge = f'<span class="delta {cls}">{arrow} {abs(d):.1f}%<em>{k["note"]}</em></span>'
    return f'''<div class="kpi g-{k["group"]}">
      <div class="kpi-label">{k["label"]}</div>
      <div class="kpi-value">{k["value"]}</div>
      <div class="kpi-foot"><span class="kpi-sub">{k.get("sub","")}</span>{badge}</div>
    </div>'''

kpis = "\n".join(kpi_html(k) for k in KPIS)


def table(headers, rows, aligns=None):
    aligns = aligns or ["left"] * len(headers)
    th = "".join(f'<th style="text-align:{a}">{h}</th>' for h, a in zip(headers, aligns))
    trs = []
    for r in rows:
        tds = "".join(f'<td style="text-align:{a}">{c}</td>' for c, a in zip(r, aligns))
        trs.append(f"<tr>{tds}</tr>")
    return f'<table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


# ---- Tables ----
countries_tbl = table(
    ["#", "Country", "Sessions", "Users", "% of total"],
    [[i + 1, c["country"], f'{int(c["sessions"]):,}', f'{int(c["totalUsers"]):,}',
      f'{c["sessions"]/sum(x["sessions"] for x in ga["countries_fy"])*100:.1f}%']
     for i, c in enumerate(ga["countries_fy"])],
    ["right", "left", "right", "right", "right"])

pages_tbl = table(
    ["#", "Page", "Pageviews", "Sessions"],
    [[i + 1, f'<a href="https://knowmax.ai{p["pagePath"]}" target="_blank">{p["pagePath"]}</a>',
      f'{int(p["screenPageViews"]):,}', f'{int(p["sessions"]):,}']
     for i, p in enumerate(ga["top_pages"])],
    ["right", "left", "right", "right"])

kw_tbl = table(
    ["#", "Keyword", "Volume", "Best pos.", "Traffic", "URL"],
    [[i + 1, k["keyword"], f'{k["volume"]:,}',
      f'<span class="pos p{min(k["best_position"],11)}">{k["best_position"]}</span>',
      f'{k["sum_traffic"]:,}',
      f'<a href="{k["url"]}" target="_blank">{k["url"].replace("https://knowmax.ai","")}</a>']
     for i, k in enumerate(seo["top_keywords"])],
    ["right", "left", "right", "center", "right", "left"])

sp_tbl = table(
    ["#", "Page", "Traffic", "Keywords", "Top keyword", "Pos."],
    [[i + 1, f'<a href="{p["url"]}" target="_blank">{p["url"].replace("https://knowmax.ai","") or "/"}</a>',
      f'{p["sum_traffic"]:,}', f'{p["keywords"]:,}', p["top_keyword"],
      f'<span class="pos p{min(p["top_keyword_best_position"],11)}">{p["top_keyword_best_position"]}</span>']
     for i, p in enumerate(seo["top_pages"])],
    ["right", "left", "right", "right", "left", "center"])

camp_rows = []
for c in ads["campaigns"]:
    cpc = c["cost_usd"] / c["clicks"] if c["clicks"] else 0
    ctr = c["clicks"] / c["impressions"] * 100 if c["impressions"] else 0
    camp_rows.append([c["campaign"], f'<span class="tag {c["status"].lower()}">{c["status"].title()}</span>',
                      f'${c["cost_usd"]:,.2f}', f'{c["impressions"]:,}', f'{c["clicks"]:,}',
                      f'{ctr:.2f}%', f'${cpc:,.2f}', f'{c["conversions"]:.0f}'])
camp_tbl = table(["Campaign", "Status", "Cost (USD)", "Impressions", "Clicks", "CTR", "CPC", "Conv."],
                 camp_rows, ["left", "left", "right", "right", "right", "right", "right", "right"])

stage_rows = [[s["stage"], f'{s["count"]}', f'{s["value"]:,.0f}'] for s in crm["deals_by_stage"]]
stage_tbl = table(["Stage", "Deals", "Value"], stage_rows, ["left", "right", "right"])

HTML = f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Knowmax Marketing Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{{
  --bg:#0f172a; --panel:#16213b; --panel2:#1c2745; --line:#27354f;
  --txt:#e2e8f0; --mut:#94a3b8; --dim:#64748b;
  --teal:#2dd4bf; --blue:#60a5fa; --amber:#fbbf24; --violet:#a78bfa;
  --green:#34d399; --red:#f87171; --pink:#f472b6;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);
  font-family:'Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  font-size:14px;line-height:1.5}}
a{{color:var(--blue);text-decoration:none}} a:hover{{text-decoration:underline}}
.wrap{{max-width:1400px;margin:0 auto;padding:28px 22px 60px}}
header{{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;
  gap:14px;margin-bottom:26px;padding-bottom:20px;border-bottom:1px solid var(--line)}}
h1{{margin:0;font-size:26px;font-weight:800;letter-spacing:-.5px}}
h1 span{{background:linear-gradient(90deg,var(--teal),var(--blue));-webkit-background-clip:text;
  background-clip:text;color:transparent}}
.sub{{color:var(--mut);font-size:13px;margin-top:6px}}
.stamp{{background:var(--panel);border:1px solid var(--line);border-radius:9px;
  padding:8px 14px;font-size:12px;color:var(--mut)}}
.stamp b{{color:var(--teal)}}

.kpis{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-bottom:28px}}
.kpi{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 15px;
  position:relative;overflow:hidden}}
.kpi::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:3px}}
.kpi.g-traffic::before{{background:var(--teal)}}
.kpi.g-seo::before{{background:var(--violet)}}
.kpi.g-ads::before{{background:var(--amber)}}
.kpi.g-crm::before{{background:var(--blue)}}
.kpi.g-ops::before{{background:var(--pink)}}
.kpi-label{{font-size:11px;text-transform:uppercase;letter-spacing:.9px;color:var(--mut);font-weight:600}}
.kpi-value{{font-size:26px;font-weight:800;margin:6px 0 2px;letter-spacing:-.7px}}
.kpi-foot{{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap}}
.kpi-sub{{font-size:11px;color:var(--dim)}}
.delta{{font-size:11px;font-weight:700;padding:2px 7px;border-radius:20px;display:inline-flex;
  align-items:center;gap:5px}}
.delta em{{font-style:normal;font-weight:500;opacity:.75;font-size:10px}}
.delta.up{{background:rgba(52,211,153,.13);color:var(--green)}}
.delta.down{{background:rgba(248,113,113,.13);color:var(--red)}}
.delta.flat{{background:rgba(148,163,184,.13);color:var(--mut)}}

.tabs{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px;border-bottom:1px solid var(--line);
  padding-bottom:0}}
.tab{{background:none;border:none;border-bottom:2px solid transparent;color:var(--mut);
  padding:10px 16px;font-size:13.5px;font-weight:600;cursor:pointer;font-family:inherit;
  border-radius:8px 8px 0 0}}
.tab:hover{{color:var(--txt);background:var(--panel)}}
.tab.on{{color:var(--teal);border-bottom-color:var(--teal)}}
.panel{{display:none}} .panel.on{{display:block}}

.grid{{display:grid;gap:14px;margin-bottom:14px}}
.g2{{grid-template-columns:1fr 1fr}}
.g3{{grid-template-columns:1fr 1fr}}
@media(max-width:900px){{.g2,.g3{{grid-template-columns:1fr}}}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.card h3{{margin:0 0 4px;font-size:14px;font-weight:700}}
.card .hint{{font-size:11.5px;color:var(--dim);margin-bottom:12px}}
.chart{{position:relative;height:290px}}
.chart.sm{{height:250px}}
.chart.tall{{height:360px}}

table{{width:100%;border-collapse:collapse;font-size:12.5px}}
thead th{{color:var(--mut);font-size:10.5px;text-transform:uppercase;letter-spacing:.7px;
  font-weight:700;padding:8px 9px;border-bottom:1px solid var(--line);white-space:nowrap}}
tbody td{{padding:8px 9px;border-bottom:1px solid rgba(39,53,79,.55)}}
tbody tr:hover{{background:var(--panel2)}}
tbody tr:last-child td{{border-bottom:none}}
.scroll{{max-height:520px;overflow:auto}}
.scroll::-webkit-scrollbar{{width:8px;height:8px}}
.scroll::-webkit-scrollbar-thumb{{background:var(--line);border-radius:8px}}
td a{{display:inline-block;max-width:420px;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;vertical-align:bottom}}
.pos{{display:inline-block;min-width:26px;padding:2px 6px;border-radius:6px;font-weight:700;
  font-size:11px;background:rgba(148,163,184,.15);color:var(--mut)}}
.pos.p1,.pos.p2,.pos.p3{{background:rgba(52,211,153,.15);color:var(--green)}}
.pos.p4,.pos.p5,.pos.p6,.pos.p7,.pos.p8,.pos.p9,.pos.p10{{background:rgba(251,191,36,.15);color:var(--amber)}}
.tag{{font-size:10.5px;padding:2px 8px;border-radius:20px;font-weight:700;text-transform:uppercase;
  letter-spacing:.5px;background:rgba(148,163,184,.15);color:var(--mut)}}
.tag.enabled{{background:rgba(52,211,153,.15);color:var(--green)}}
.tag.paused{{background:rgba(251,191,36,.15);color:var(--amber)}}
.note{{background:var(--panel2);border-left:3px solid var(--amber);border-radius:8px;
  padding:11px 14px;font-size:12.5px;color:var(--mut);margin-bottom:14px}}
footer{{margin-top:34px;padding-top:18px;border-top:1px solid var(--line);
  font-size:11.5px;color:var(--dim);display:flex;justify-content:space-between;
  flex-wrap:wrap;gap:10px}}
</style></head><body>
<div class="wrap">
<header>
  <div>
    <h1>Knowmax <span>Marketing Dashboard</span></h1>
    <div class="sub">GA4 · Ahrefs &amp; Search Console · Google Ads · Zoho CRM · Snov.io</div>
  </div>
  <div class="stamp">Last refreshed <b>{gen}</b></div>
</header>

<div class="kpis">{kpis}</div>

<div class="tabs">
  <button class="tab on" data-p="traffic">Website Traffic</button>
  <button class="tab" data-p="seo">SEO &amp; Search</button>
  <button class="tab" data-p="ads">Google Ads</button>
  <button class="tab" data-p="crm">CRM Pipeline</button>
</div>

<!-- TRAFFIC -->
<section class="panel on" id="p-traffic">
  <div class="card" style="margin-bottom:14px">
    <h3>Monthly traffic trend</h3>
    <div class="hint">Sessions, users and pageviews · Aug 2025 – Aug 2026 (Aug 2026 is month-to-date)</div>
    <div class="chart tall"><canvas id="c-monthly"></canvas></div>
  </div>
  <div class="grid g2">
    <div class="card"><h3>Sessions by channel</h3>
      <div class="hint">Trailing 12 months</div>
      <div class="chart"><canvas id="c-channels"></canvas></div></div>
    <div class="card"><h3>Sessions by device</h3>
      <div class="hint">Trailing 12 months</div>
      <div class="chart"><canvas id="c-devices"></canvas></div></div>
  </div>
  <div class="grid g2">
    <div class="card"><h3>Top 20 countries</h3>
      <div class="hint">FY 2025–26 scope · Apr 2025 – Mar 2026</div>
      <div class="scroll">{countries_tbl}</div></div>
    <div class="card"><h3>Top 20 pages</h3>
      <div class="hint">Trailing 12 months by pageviews</div>
      <div class="scroll">{pages_tbl}</div></div>
  </div>
</section>

<!-- SEO -->
<section class="panel" id="p-seo">
  <div class="card" style="margin-bottom:14px">
    <h3>Search Console performance</h3>
    <div class="hint">Monthly clicks (bars) and impressions (line) · knowmax.ai</div>
    <div class="chart tall"><canvas id="c-gsc"></canvas></div>
  </div>
  <div class="card" style="margin-bottom:14px">
    <h3>Average position &amp; CTR</h3>
    <div class="hint">Lower position is better</div>
    <div class="chart sm"><canvas id="c-gscpos"></canvas></div>
  </div>
  <div class="card" style="margin-bottom:14px">
    <h3>Top 20 organic keywords</h3>
    <div class="hint">Ahrefs · ranked by estimated monthly traffic</div>
    <div class="scroll">{kw_tbl}</div>
  </div>
  <div class="card">
    <h3>Top 20 organic pages</h3>
    <div class="hint">Ahrefs · ranked by estimated monthly traffic</div>
    <div class="scroll">{sp_tbl}</div>
  </div>
</section>

<!-- ADS -->
<section class="panel" id="p-ads">
  <div class="note"><b>Heads up:</b> the Google Ads account has recorded no spend, clicks or
  impressions since December 2025. All paid campaigns are currently paused, so current-month and
  last-month figures are zero. Figures below cover the trailing 12 months.</div>
  <div class="card" style="margin-bottom:14px">
    <h3>Monthly ad spend &amp; clicks</h3>
    <div class="hint">Cost converted from INR at ₹84.5 = $1</div>
    <div class="chart"><canvas id="c-ads"></canvas></div>
  </div>
  <div class="card">
    <h3>Campaign breakdown</h3>
    <div class="hint">Campaigns with delivery in the trailing 12 months</div>
    {camp_tbl}
  </div>
</section>

<!-- CRM -->
<section class="panel" id="p-crm">
  <div class="grid g2">
    <div class="card"><h3>Leads by status</h3>
      <div class="hint">{crm["leads_total"]:,} leads across 9 tracked owners</div>
      <div class="chart"><canvas id="c-lstatus"></canvas></div></div>
    <div class="card"><h3>Leads by source</h3>
      <div class="hint">Top acquisition sources</div>
      <div class="chart"><canvas id="c-lsource"></canvas></div></div>
  </div>
  <div class="grid g2">
    <div class="card"><h3>Leads by owner</h3>
      <div class="hint">Distribution across the sales team</div>
      <div class="chart sm"><canvas id="c-lowner"></canvas></div></div>
    <div class="card"><h3>Deals by stage</h3>
      <div class="hint">{crm["deals_total"]} deals · {open_count} still open</div>
      <div class="chart sm"><canvas id="c-dstage"></canvas></div></div>
  </div>
  <div class="grid g2">
    <div class="card"><h3>Pipeline value by stage</h3>
      <div class="hint">Amounts in Zoho CRM default currency</div>
      {stage_tbl}</div>
    <div class="card"><h3>Deals by owner</h3>
      <div class="hint">Deal count per owner</div>
      <div class="chart sm"><canvas id="c-downer"></canvas></div></div>
  </div>
</section>

<footer>
  <span>Knowmax Marketing Dashboard · generated {gen} · all data embedded, no live calls</span>
  <span>Sources: GA4 property 251430515 · Ahrefs project 1715938 · Google Ads 7735901637 · Zoho CRM · Snov.io</span>
</footer>
</div>

<script>
const D = {json.dumps(DATA)};

// tabs
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(x=>x.classList.remove('on'));
  t.classList.add('on');
  document.getElementById('p-'+t.dataset.p).classList.add('on');
}});

const C={{teal:'#2dd4bf',blue:'#60a5fa',amber:'#fbbf24',violet:'#a78bfa',green:'#34d399',
  red:'#f87171',pink:'#f472b6',orange:'#fb923c',cyan:'#22d3ee',lime:'#a3e635',
  slate:'#94a3b8',indigo:'#818cf8'}};
const PAL=[C.teal,C.blue,C.amber,C.violet,C.green,C.pink,C.orange,C.cyan,C.lime,C.indigo,C.red,C.slate];
Chart.defaults.color='#94a3b8';
Chart.defaults.font.family="'Plus Jakarta Sans',-apple-system,'Segoe UI',sans-serif";
Chart.defaults.font.size=11;
const GRID={{color:'rgba(39,53,79,.7)'}};
const LEG={{labels:{{boxWidth:10,boxHeight:10,usePointStyle:true,pointStyle:'circle',padding:14}}}};

function mlabel(ym){{
  const y=ym.slice(0,4), m=parseInt(ym.slice(4,6))-1;
  return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m]+" '"+y.slice(2);
}}
function mlabel2(s){{
  const [y,m]=s.split('-');
  return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][parseInt(m)-1]+" '"+y.slice(2);
}}

// 1. Monthly traffic
new Chart(document.getElementById('c-monthly'),{{
  data:{{labels:D.ga.monthly.map(r=>mlabel(r.yearMonth)),
    datasets:[
      {{type:'bar',label:'Sessions',data:D.ga.monthly.map(r=>r.sessions),
        backgroundColor:'rgba(45,212,191,.75)',borderRadius:4,order:3}},
      {{type:'bar',label:'Users',data:D.ga.monthly.map(r=>r.totalUsers),
        backgroundColor:'rgba(96,165,250,.75)',borderRadius:4,order:3}},
      {{type:'line',label:'Pageviews',data:D.ga.monthly.map(r=>r.screenPageViews),
        borderColor:C.amber,backgroundColor:C.amber,tension:.35,pointRadius:3,borderWidth:2,order:1}}
    ]}},
  options:{{maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:LEG}},
    scales:{{x:{{grid:{{display:false}}}},y:{{grid:GRID,beginAtZero:true,
      ticks:{{callback:v=>v>=1000?(v/1000)+'k':v}}}}}}}}
}});

// 2. Channels donut
new Chart(document.getElementById('c-channels'),{{type:'doughnut',
  data:{{labels:D.ga.channels.map(r=>r.sessionDefaultChannelGroup),
    datasets:[{{data:D.ga.channels.map(r=>r.sessions),backgroundColor:PAL,
      borderColor:'#16213b',borderWidth:2}}]}},
  options:{{maintainAspectRatio:false,cutout:'58%',
    plugins:{{legend:{{position:'right',...LEG}},
      tooltip:{{callbacks:{{label:c=>{{
        const t=c.dataset.data.reduce((a,b)=>a+b,0);
        return ' '+c.label+': '+c.raw.toLocaleString()+' ('+(c.raw/t*100).toFixed(1)+'%)';}}}}}}}}}}
}});

// 3. Devices donut
new Chart(document.getElementById('c-devices'),{{type:'doughnut',
  data:{{labels:D.ga.devices.map(r=>r.deviceCategory),
    datasets:[{{data:D.ga.devices.map(r=>r.sessions),
      backgroundColor:[C.teal,C.violet,C.amber,C.pink],borderColor:'#16213b',borderWidth:2}}]}},
  options:{{maintainAspectRatio:false,cutout:'58%',
    plugins:{{legend:{{position:'right',...LEG}},
      tooltip:{{callbacks:{{label:c=>{{
        const t=c.dataset.data.reduce((a,b)=>a+b,0);
        return ' '+c.label+': '+c.raw.toLocaleString()+' ('+(c.raw/t*100).toFixed(1)+'%)';}}}}}}}}}}
}});

// 4. GSC clicks + impressions
new Chart(document.getElementById('c-gsc'),{{
  data:{{labels:D.seo.gsc_monthly.map(r=>mlabel2(r.date)),
    datasets:[
      {{type:'bar',label:'Clicks',data:D.seo.gsc_monthly.map(r=>r.clicks),
        backgroundColor:'rgba(45,212,191,.8)',borderRadius:4,yAxisID:'y'}},
      {{type:'line',label:'Impressions',data:D.seo.gsc_monthly.map(r=>r.impressions),
        borderColor:C.violet,backgroundColor:'rgba(167,139,250,.12)',fill:true,
        tension:.35,pointRadius:3,borderWidth:2,yAxisID:'y1'}}
    ]}},
  options:{{maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:LEG}},
    scales:{{x:{{grid:{{display:false}}}},
      y:{{position:'left',grid:GRID,beginAtZero:true,title:{{display:true,text:'Clicks'}},
        ticks:{{callback:v=>v>=1000?(v/1000)+'k':v}}}},
      y1:{{position:'right',grid:{{display:false}},beginAtZero:true,
        title:{{display:true,text:'Impressions'}},
        ticks:{{callback:v=>v>=1e6?(v/1e6)+'M':(v>=1000?(v/1000)+'k':v)}}}}}}}}
}});

// 5. GSC position + CTR
new Chart(document.getElementById('c-gscpos'),{{
  data:{{labels:D.seo.gsc_monthly.map(r=>mlabel2(r.date)),
    datasets:[
      {{type:'line',label:'Avg position',data:D.seo.gsc_monthly.map(r=>r.position),
        borderColor:C.amber,backgroundColor:C.amber,tension:.35,pointRadius:3,borderWidth:2,yAxisID:'y'}},
      {{type:'line',label:'CTR %',data:D.seo.gsc_monthly.map(r=>+(r.ctr*100).toFixed(2)),
        borderColor:C.green,backgroundColor:C.green,tension:.35,pointRadius:3,borderWidth:2,
        borderDash:[5,4],yAxisID:'y1'}}
    ]}},
  options:{{maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:LEG}},
    scales:{{x:{{grid:{{display:false}}}},
      y:{{position:'left',grid:GRID,reverse:true,title:{{display:true,text:'Avg position'}}}},
      y1:{{position:'right',grid:{{display:false}},beginAtZero:true,
        title:{{display:true,text:'CTR %'}}}}}}}}
}});

// 6. Ads monthly
new Chart(document.getElementById('c-ads'),{{
  data:{{labels:D.ads.monthly.map(r=>mlabel2(r.month)),
    datasets:[
      {{type:'bar',label:'Spend (USD)',data:D.ads.monthly.map(r=>+r.cost_usd.toFixed(2)),
        backgroundColor:'rgba(251,191,36,.8)',borderRadius:4,yAxisID:'y'}},
      {{type:'line',label:'Clicks',data:D.ads.monthly.map(r=>r.clicks),
        borderColor:C.blue,backgroundColor:C.blue,tension:.35,pointRadius:4,borderWidth:2,yAxisID:'y1'}}
    ]}},
  options:{{maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:LEG}},
    scales:{{x:{{grid:{{display:false}}}},
      y:{{position:'left',grid:GRID,beginAtZero:true,title:{{display:true,text:'USD'}}}},
      y1:{{position:'right',grid:{{display:false}},beginAtZero:true,
        title:{{display:true,text:'Clicks'}}}}}}}}
}});

// horizontal bar helper
function hbar(id,labels,values,color,fmt){{
  new Chart(document.getElementById(id),{{type:'bar',
    data:{{labels:labels,datasets:[{{data:values,backgroundColor:color,borderRadius:4,
      barThickness:'flex',maxBarThickness:26}}]}},
    options:{{indexAxis:'y',maintainAspectRatio:false,
      plugins:{{legend:{{display:false}},
        tooltip:{{callbacks:{{label:c=>' '+(fmt?fmt(c.raw):c.raw.toLocaleString())}}}}}},
      scales:{{x:{{grid:GRID,beginAtZero:true,
        ticks:{{callback:v=>v>=1000?(v/1000)+'k':v}}}},
        y:{{grid:{{display:false}}}}}}}}
  }});
}}

hbar('c-lstatus',D.crm.leads_by_status.map(r=>r[0]),D.crm.leads_by_status.map(r=>r[1]),
  'rgba(45,212,191,.8)');
hbar('c-lsource',D.crm.leads_by_source.map(r=>r[0]),D.crm.leads_by_source.map(r=>r[1]),
  'rgba(96,165,250,.8)');
hbar('c-lowner',D.crm.leads_by_owner.map(r=>r[0]),D.crm.leads_by_owner.map(r=>r[1]),
  'rgba(167,139,250,.8)');
hbar('c-dstage',D.crm.deals_by_stage.map(r=>r.stage),D.crm.deals_by_stage.map(r=>r.count),
  'rgba(251,191,36,.8)');
hbar('c-downer',D.crm.deals_by_owner.map(r=>r[0]),D.crm.deals_by_owner.map(r=>r[1]),
  'rgba(244,114,182,.8)');
</script>
</body></html>
'''

open("Marketing_Dashboard.html", "w").write(HTML)
print("built", len(HTML), "bytes")
