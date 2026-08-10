"""
Builds a single self-contained HTML dashboard (dashboard.html) with all
the SQL results rendered as interactive Chart.js charts, plus the latest
AI-generated insights summary. Data is baked in as JSON at generation
time, so the file opens standalone in any browser — no server, no DB
connection needed at view time (only Chart.js loads from a CDN).

Usage:
    python3 scripts/generate_dashboard.py
    # then open dashboard.html in a browser
"""
import sqlite3
import os
import json
import re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = f"{BASE}/spotify_analytics.sqlite"
OUTPUT_PATH = f"{BASE}/dashboard.html"
INSIGHTS_PATH = f"{BASE}/insights_report.md"


def get_conn():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)


def get_data(conn):
    data = {}

    data["skip_by_genre"] = conn.execute("""
        SELECT t.track_genre, ROUND(100.0 * SUM(le.skipped) / COUNT(*), 1)
        FROM listen_events le JOIN tracks t ON t.track_id = le.track_id
        GROUP BY t.track_genre HAVING COUNT(*) >= 50
        ORDER BY 2 DESC LIMIT 12
    """).fetchall()

    data["weekly_trend"] = conn.execute("""
        SELECT week_number, COUNT(*), COUNT(DISTINCT user_id)
        FROM listen_events GROUP BY week_number ORDER BY week_number
    """).fetchall()

    retention_rows = conn.execute("""
        WITH wu AS (SELECT DISTINCT user_id, week_number FROM listen_events)
        SELECT a.week_number,
               ROUND(100.0 * COUNT(DISTINCT b.user_id) / COUNT(DISTINCT a.user_id), 1)
        FROM wu a LEFT JOIN wu b ON a.user_id = b.user_id AND b.week_number = a.week_number + 1
        GROUP BY a.week_number ORDER BY a.week_number
    """).fetchall()
    data["retention"] = retention_rows[:-1]  # drop boundary-artifact last week

    data["power_users"] = conn.execute("""
        WITH ut AS (
            SELECT user_id, COUNT(*) AS plays, ROUND(100.0*SUM(skipped)/COUNT(*),1) AS skip_pct
            FROM listen_events GROUP BY user_id
        ), ranked AS (SELECT *, NTILE(4) OVER (ORDER BY plays DESC) AS q FROM ut)
        SELECT q, ROUND(AVG(plays),1), ROUND(AVG(skip_pct),1) FROM ranked GROUP BY q ORDER BY q
    """).fetchall()

    diversity_rows = conn.execute("""
        WITH ud AS (
            SELECT le.user_id, COUNT(*) AS plays, COUNT(DISTINCT t.track_genre) AS genres
            FROM listen_events le JOIN tracks t ON t.track_id = le.track_id GROUP BY le.user_id
        )
        SELECT CASE WHEN plays>=100 THEN 'high_volume' WHEN plays>=30 THEN 'mid_volume' ELSE 'low_volume' END,
               ROUND(AVG(genres),1)
        FROM ud GROUP BY 1
    """).fetchall()
    order = {"low_volume": 0, "mid_volume": 1, "high_volume": 2}
    data["diversity"] = sorted(diversity_rows, key=lambda r: order[r[0]])

    data["plan_comparison"] = conn.execute("""
        SELECT u.plan_type, ROUND(1.0*COUNT(*)/COUNT(DISTINCT le.user_id),1),
               ROUND(100.0*SUM(le.skipped)/COUNT(*),1)
        FROM listen_events le JOIN users u ON u.user_id = le.user_id GROUP BY u.plan_type
    """).fetchall()

    data["top_tracks"] = conn.execute("""
        SELECT t.track_name, t.artists, t.track_genre, COUNT(*) AS plays,
               ROUND(100.0*SUM(CASE WHEN le.skipped=0 THEN 1 ELSE 0 END)/COUNT(*),1) AS completion_pct
        FROM listen_events le JOIN tracks t ON t.track_id = le.track_id
        GROUP BY t.track_id HAVING COUNT(*) >= 5
        ORDER BY completion_pct DESC, plays DESC LIMIT 10
    """).fetchall()

    return data


def get_latest_summary():
    if not os.path.exists(INSIGHTS_PATH):
        return "Run scripts/generate_insights.py first to generate the AI summary."
    text = open(INSIGHTS_PATH, encoding="utf-8").read()
    m = re.search(r"## AI-Generated Summary\n\n(.+?)\n\n---", text, re.S)
    return m.group(1).strip() if m else "Summary not found."


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Spotify Product Analytics Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  :root {{ --accent:#1DB954; --bg:#0f0f0f; --card:#181818; --text:#e8e8e8; --muted:#9a9a9a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  header {{ padding:28px 32px 16px; border-bottom:1px solid #2a2a2a; }}
  header h1 {{ margin:0 0 4px; font-size:22px; }}
  header p {{ margin:0; color:var(--muted); font-size:13px; }}
  .summary {{ margin:20px 32px; padding:18px 22px; background:var(--card); border-left:4px solid var(--accent); border-radius:6px; white-space:pre-wrap; line-height:1.55; font-size:14px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(420px,1fr)); gap:20px; padding:8px 32px 40px; }}
  .card {{ background:var(--card); border-radius:10px; padding:18px; }}
  .card h3 {{ margin:0 0 12px; font-size:14px; color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:.04em; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid #2a2a2a; }}
  th {{ color:var(--muted); font-weight:600; }}
  canvas {{ max-height:280px; }}
</style>
</head>
<body>
<header>
  <h1>Spotify Product Analytics Dashboard</h1>
  <p>Generated {generated_at} &middot; SQL analysis + AI-generated insights</p>
</header>

<div class="summary">{summary}</div>

<div class="grid">
  <div class="card"><h3>Skip Rate by Genre (top 12)</h3><canvas id="chartSkip"></canvas></div>
  <div class="card"><h3>Weekly Engagement Trend</h3><canvas id="chartTrend"></canvas></div>
  <div class="card"><h3>Week-over-Week Retention</h3><canvas id="chartRetention"></canvas></div>
  <div class="card"><h3>Power User Segmentation (avg plays/user)</h3><canvas id="chartPower"></canvas></div>
  <div class="card"><h3>Genre Diversity by Volume Bucket</h3><canvas id="chartDiversity"></canvas></div>
  <div class="card"><h3>Free vs Premium</h3><canvas id="chartPlan"></canvas></div>
  <div class="card" style="grid-column:1/-1">
    <h3>Top Tracks by Completion Rate</h3>
    <table>
      <thead><tr><th>Track</th><th>Artist</th><th>Genre</th><th>Plays</th><th>Completion %</th></tr></thead>
      <tbody id="topTracksBody"></tbody>
    </table>
  </div>
</div>

<script>
const DATA = {data_json};

Chart.defaults.color = "#9a9a9a";
Chart.defaults.borderColor = "#2a2a2a";
const ACCENT = "#1DB954";
const ACCENT2 = "#535353";

new Chart(document.getElementById("chartSkip"), {{
  type: "bar",
  data: {{ labels: DATA.skip_by_genre.map(r => r[0]),
           datasets: [{{ label: "Skip rate %", data: DATA.skip_by_genre.map(r => r[1]), backgroundColor: ACCENT }}] }},
  options: {{ indexAxis: "y", plugins: {{ legend: {{ display:false }} }} }}
}});

new Chart(document.getElementById("chartTrend"), {{
  type: "line",
  data: {{ labels: DATA.weekly_trend.map(r => "W"+r[0]),
           datasets: [
             {{ label: "Total plays", data: DATA.weekly_trend.map(r => r[1]), borderColor: ACCENT, backgroundColor: ACCENT, tension:.3 }},
             {{ label: "Active users", data: DATA.weekly_trend.map(r => r[2]), borderColor: ACCENT2, backgroundColor: ACCENT2, tension:.3, yAxisID: "y1" }}
           ] }},
  options: {{ scales: {{ y1: {{ position:"right", grid:{{drawOnChartArea:false}} }} }} }}
}});

new Chart(document.getElementById("chartRetention"), {{
  type: "line",
  data: {{ labels: DATA.retention.map(r => "W"+r[0]),
           datasets: [{{ label: "Retention %", data: DATA.retention.map(r => r[1]), borderColor: ACCENT, backgroundColor: ACCENT+"33", fill:true, tension:.3 }}] }},
  options: {{ scales: {{ y: {{ min:80, max:100 }} }} }}
}});

new Chart(document.getElementById("chartPower"), {{
  type: "bar",
  data: {{ labels: DATA.power_users.map(r => "Q"+r[0]),
           datasets: [{{ label: "Avg plays/user", data: DATA.power_users.map(r => r[1]), backgroundColor: [ACCENT,"#4CAF50","#81C784","#C8E6C9"] }}] }},
  options: {{ plugins: {{ legend: {{ display:false }} }} }}
}});

new Chart(document.getElementById("chartDiversity"), {{
  type: "bar",
  data: {{ labels: DATA.diversity.map(r => r[0].replace("_"," ")),
           datasets: [{{ label: "Avg distinct genres", data: DATA.diversity.map(r => r[1]), backgroundColor: ACCENT }}] }},
  options: {{ plugins: {{ legend: {{ display:false }} }} }}
}});

new Chart(document.getElementById("chartPlan"), {{
  type: "bar",
  data: {{ labels: DATA.plan_comparison.map(r => r[0]),
           datasets: [
             {{ label: "Avg plays/user", data: DATA.plan_comparison.map(r => r[1]), backgroundColor: ACCENT }},
             {{ label: "Skip rate %", data: DATA.plan_comparison.map(r => r[2]), backgroundColor: ACCENT2 }}
           ] }}
}});

const tbody = document.getElementById("topTracksBody");
DATA.top_tracks.forEach(r => {{
  const tr = document.createElement("tr");
  tr.innerHTML = `<td>${{r[0]}}</td><td>${{r[1]}}</td><td>${{r[2]}}</td><td>${{r[3]}}</td><td>${{r[4]}}%</td>`;
  tbody.appendChild(tr);
}});
</script>
</body>
</html>
"""


def main():
    conn = get_conn()
    data = get_data(conn)
    conn.close()

    html = HTML_TEMPLATE.format(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        summary=get_latest_summary(),
        data_json=json.dumps(data),
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard written to {OUTPUT_PATH} — open it in a browser.")


if __name__ == "__main__":
    main()
