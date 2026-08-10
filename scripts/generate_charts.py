"""
Generates PNG charts from the same SQL analysis behind insights_report.md,
so the project has visual output (not just tables), suitable for embedding
in the README on GitHub.

Usage:
    python3 scripts/generate_charts.py
"""
import sqlite3
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = f"{BASE}/spotify_analytics.sqlite"
CHARTS_DIR = f"{BASE}/charts"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#444444",
    "axes.grid": True,
    "grid.color": "#e0e0e0",
    "grid.linestyle": "--",
    "font.size": 11,
})

ACCENT = "#1DB954"   # Spotify green, why not
ACCENT2 = "#535353"


def get_conn():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)


def save(fig, name):
    os.makedirs(CHARTS_DIR, exist_ok=True)
    path = f"{CHARTS_DIR}/{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved {path}")


def chart_skip_rate_by_genre(conn):
    rows = conn.execute("""
        SELECT t.track_genre, ROUND(100.0 * SUM(le.skipped) / COUNT(*), 1) AS skip_rate_pct
        FROM listen_events le JOIN tracks t ON t.track_id = le.track_id
        GROUP BY t.track_genre
        HAVING COUNT(*) >= 50
        ORDER BY skip_rate_pct DESC
        LIMIT 12
    """).fetchall()
    genres = [r[0] for r in rows][::-1]
    rates = [r[1] for r in rows][::-1]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(genres, rates, color=ACCENT)
    ax.set_xlabel("Skip rate (%)")
    ax.set_title("Top 12 Genres by Skip Rate")
    for i, v in enumerate(rates):
        ax.text(v + 0.3, i, f"{v}%", va="center", fontsize=9)
    save(fig, "01_skip_rate_by_genre")


def chart_weekly_engagement(conn):
    rows = conn.execute("""
        SELECT week_number, COUNT(*) AS total_plays, COUNT(DISTINCT user_id) AS active_users
        FROM listen_events GROUP BY week_number ORDER BY week_number
    """).fetchall()
    weeks = [r[0] for r in rows]
    plays = [r[1] for r in rows]
    users = [r[2] for r in rows]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax2 = ax1.twinx()
    ax1.plot(weeks, plays, marker="o", color=ACCENT, linewidth=2, label="Total plays")
    ax2.plot(weeks, users, marker="s", color=ACCENT2, linewidth=2, linestyle="--", label="Active users")
    ax1.set_xlabel("Week")
    ax1.set_ylabel("Total plays", color=ACCENT)
    ax2.set_ylabel("Active users", color=ACCENT2)
    ax1.set_title("Weekly Engagement Trend")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    save(fig, "02_weekly_engagement_trend")


def chart_retention(conn):
    rows = conn.execute("""
        WITH weekly_users AS (SELECT DISTINCT user_id, week_number FROM listen_events)
        SELECT a.week_number,
               ROUND(100.0 * COUNT(DISTINCT b.user_id) / COUNT(DISTINCT a.user_id), 1) AS retention_pct
        FROM weekly_users a
        LEFT JOIN weekly_users b ON a.user_id = b.user_id AND b.week_number = a.week_number + 1
        GROUP BY a.week_number ORDER BY a.week_number
    """).fetchall()
    # drop the last week — it's a boundary artifact (no week+1 to measure against)
    rows = rows[:-1]
    weeks = [r[0] for r in rows]
    retention = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(weeks, retention, marker="o", color=ACCENT, linewidth=2)
    ax.fill_between(weeks, retention, min(retention) - 5, color=ACCENT, alpha=0.1)
    ax.set_xlabel("Week")
    ax.set_ylabel("Retention to next week (%)")
    ax.set_title("Week-over-Week Retention")
    ax.set_ylim(min(retention) - 5, 100)
    for x, y in zip(weeks, retention):
        ax.text(x, y + 0.5, f"{y}%", ha="center", fontsize=9)
    save(fig, "03_retention_curve")


def chart_power_user_segments(conn):
    rows = conn.execute("""
        WITH user_totals AS (
            SELECT user_id, COUNT(*) AS total_plays,
                   ROUND(100.0 * SUM(skipped) / COUNT(*), 1) AS skip_rate_pct
            FROM listen_events GROUP BY user_id
        ),
        ranked AS (SELECT *, NTILE(4) OVER (ORDER BY total_plays DESC) AS q FROM user_totals)
        SELECT q, ROUND(AVG(total_plays), 1), ROUND(AVG(skip_rate_pct), 1)
        FROM ranked GROUP BY q ORDER BY q
    """).fetchall()
    labels = [f"Q{r[0]}" for r in rows]
    avg_plays = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, avg_plays, color=[ACCENT, "#4CAF50", "#81C784", "#C8E6C9"])
    ax.set_xlabel("Engagement quartile (Q1 = most engaged)")
    ax.set_ylabel("Avg plays per user")
    ax.set_title("Power User Segmentation")
    for b, v in zip(bars, avg_plays):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, str(v), ha="center", fontsize=9)
    save(fig, "04_power_user_segmentation")


def chart_genre_diversity(conn):
    rows = conn.execute("""
        WITH user_diversity AS (
            SELECT le.user_id, COUNT(*) AS total_plays, COUNT(DISTINCT t.track_genre) AS distinct_genres
            FROM listen_events le JOIN tracks t ON t.track_id = le.track_id GROUP BY le.user_id
        )
        SELECT CASE WHEN total_plays >= 100 THEN 'high_volume'
                    WHEN total_plays >= 30 THEN 'mid_volume' ELSE 'low_volume' END AS bucket,
               ROUND(AVG(distinct_genres), 1)
        FROM user_diversity GROUP BY bucket
    """).fetchall()
    order = {"low_volume": 0, "mid_volume": 1, "high_volume": 2}
    rows = sorted(rows, key=lambda r: order[r[0]])
    labels = [r[0].replace("_", " ").title() for r in rows]
    diversity = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, diversity, color=ACCENT)
    ax.set_ylabel("Avg distinct genres listened to")
    ax.set_title("Genre Diversity by User Engagement Level")
    for b, v in zip(bars, diversity):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, str(v), ha="center", fontsize=9)
    save(fig, "05_genre_diversity")


def chart_plan_comparison(conn):
    rows = conn.execute("""
        SELECT u.plan_type,
               ROUND(1.0 * COUNT(*) / COUNT(DISTINCT le.user_id), 1) AS avg_plays_per_user,
               ROUND(100.0 * SUM(le.skipped) / COUNT(*), 1) AS skip_rate_pct
        FROM listen_events le JOIN users u ON u.user_id = le.user_id
        GROUP BY u.plan_type
    """).fetchall()
    labels = [r[0] for r in rows]
    avg_plays = [r[1] for r in rows]
    skip_rate = [r[2] for r in rows]

    x = range(len(labels))
    fig, ax1 = plt.subplots(figsize=(7, 5))
    ax2 = ax1.twinx()
    w = 0.35
    ax1.bar([i - w / 2 for i in x], avg_plays, width=w, color=ACCENT, label="Avg plays/user")
    ax2.bar([i + w / 2 for i in x], skip_rate, width=w, color=ACCENT2, label="Skip rate %")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("Avg plays per user", color=ACCENT)
    ax2.set_ylabel("Skip rate (%)", color=ACCENT2)
    ax1.set_title("Free vs Premium: Engagement & Skip Rate")
    fig.legend(loc="upper right", bbox_to_anchor=(0.9, 0.88))
    save(fig, "06_plan_type_comparison")


def main():
    conn = get_conn()
    chart_skip_rate_by_genre(conn)
    chart_weekly_engagement(conn)
    chart_retention(conn)
    chart_power_user_segments(conn)
    chart_genre_diversity(conn)
    chart_plan_comparison(conn)
    conn.close()
    print("\nAll charts generated in charts/")


if __name__ == "__main__":
    main()
