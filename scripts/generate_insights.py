"""
Runs the core SQL analysis queries against spotify_analytics.db and sends
the results to Groq's LLM API to auto-generate a plain-English product
insights summary — the "AI analyst" layer on top of the SQL layer.

Usage:
    export GROQ_API_KEY=your_key_here   # or put it in a .env file next to this script
    python3 scripts/generate_insights.py
"""
import sqlite3
import os
import re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = f"{BASE}/spotify_analytics.sqlite"
SQL_PATH = f"{BASE}/sql/analysis_queries.sql"
OUTPUT_PATH = f"{BASE}/insights_report.md"


def load_env_file():
    """Minimal .env loader so we don't need an extra dependency."""
    env_path = f"{BASE}/.env"
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_named_queries():
    """Split analysis_queries.sql into (title, sql) pairs using the '-- N. TITLE' comments."""
    text = open(SQL_PATH, encoding="utf-8").read()
    blocks = re.split(r"\n\n\n", text)
    named = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m = re.search(r"--\s*\d+\.\s*(.+)", block)
        title = m.group(1).strip() if m else "Untitled query"
        named.append((title, block))
    return named


def run_queries():
    # read-only/immutable mode avoids file-locking issues on some network/
    # container-mounted filesystems that don't support SQLite's journal locks
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
    results = []
    for title, sql in get_named_queries():
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        results.append({"title": title, "columns": cols, "rows": rows})
    conn.close()
    return results


def format_results_as_markdown(results, row_limit=None):
    """Renders each query's results as a proper Markdown table (with the
    header-separator row), so it actually renders as a table, not a wall
    of pipe-separated text."""
    lines = []
    for r in results:
        lines.append(f"### {r['title']}")
        header = r["columns"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        rows = r["rows"] if row_limit is None else r["rows"][:row_limit]
        for row in rows:
            lines.append("| " + " | ".join(str(v) for v in row) + " |")
        lines.append("")
    return "\n".join(lines)


def format_results_as_plain_text(results, row_limit=10):
    """Compact plain-text version (used for the LLM prompt, not the report —
    cheaper on tokens and the model doesn't need markdown formatting)."""
    lines = []
    for r in results:
        lines.append(f"### {r['title']}")
        lines.append(" | ".join(r["columns"]))
        for row in r["rows"][:row_limit]:
            lines.append(" | ".join(str(v) for v in row))
        lines.append("")
    return "\n".join(lines)


def compute_derived_metrics(results):
    """
    Pre-computes deltas/ratios/flags in Python (reliable, exact) instead of
    asking the LLM to do arithmetic on raw counts (unreliable — LLMs get
    percentages and deltas wrong, or inconsistent, when left to calculate
    from tables themselves). The LLM's job becomes pure synthesis over
    trustworthy numbers, not a calculator.
    """
    by_title = {r["title"]: r for r in results}
    facts = []

    trend = by_title.get("WEEKLY ENGAGEMENT TREND")
    if trend and len(trend["rows"]) >= 2:
        first, last = trend["rows"][0], trend["rows"][-1]
        plays_pct = round(100 * (last[1] - first[1]) / first[1], 1)
        users_pct = round(100 * (last[2] - first[2]) / first[2], 1)
        facts.append(
            f"- Total plays changed {plays_pct:+g}% from week {first[0]} to week {last[0]} "
            f"({first[1]} -> {last[1]})."
        )
        facts.append(
            f"- Active users changed {users_pct:+g}% from week {first[0]} to week {last[0]} "
            f"({first[2]} -> {last[2]})."
        )

    retention = by_title.get("WEEK-OVER-WEEK RETENTION")
    if retention and len(retention["rows"]) >= 2:
        valid = [r for r in retention["rows"] if r[2] > 0]  # drop boundary week with no next-week data
        if valid:
            best = max(valid, key=lambda r: r[3])
            worst = min(valid, key=lambda r: r[3])
            facts.append(
                f"- Retention ranged from {worst[3]}% (week {worst[0]}) to {best[3]}% (week {best[0]})."
            )

    skip = by_title.get("SKIP RATE BY GENRE")
    if skip and skip["rows"]:
        # NOTE: this query is already sorted DESC and limited to the worst
        # offenders, so "lowest shown" here means least-bad among the worst
        # genres, not the best-performing genre overall.
        worst, least_bad_of_shown = skip["rows"][0], skip["rows"][-1]
        gap = round(worst[3] - least_bad_of_shown[3], 1)
        facts.append(
            f"- Among the highest-skip genres (min 50 plays), rates range from "
            f"{worst[0]} at {worst[3]}% down to {least_bad_of_shown[0]} at "
            f"{least_bad_of_shown[3]}% ({gap}-point spread) — these are still all "
            f"above-average skip rates, not a 'best' genre."
        )

    power = by_title.get("POWER USER SEGMENTATION (window functions)")
    if power and len(power["rows"]) == 4:
        q1, q4 = power["rows"][0], power["rows"][-1]
        ratio = round(q1[2] / q4[2], 1) if q4[2] else None
        facts.append(
            f"- The most engaged quartile (Q1) plays {ratio}x more than the least engaged "
            f"quartile (Q4): {q1[2]} vs {q4[2]} avg plays/user, with nearly identical skip rates "
            f"({q1[3]}% vs {q4[3]}%)."
        )

    plan = by_title.get("PLAN TYPE COMPARISON")
    if plan and len(plan["rows"]) == 2:
        rows_by_plan = {r[0]: r for r in plan["rows"]}
        if "free" in rows_by_plan and "premium" in rows_by_plan:
            f, p = rows_by_plan["free"], rows_by_plan["premium"]
            facts.append(
                f"- Free-plan users average {f[3]} plays/user vs {p[3]} for premium, "
                f"with skip rates of {f[4]}% (free) vs {p[4]}% (premium)."
            )

    return "\n".join(facts) if facts else "(no derived metrics available)"


def get_ai_summary(results_text, derived_metrics_text):
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    system_prompt = (
        "You are a senior product analyst writing a weekly readout for a product "
        "manager at a music streaming company. You will be given (1) raw SQL query "
        "result tables and (2) a set of pre-computed, verified metrics (deltas, "
        "ratios, gaps) — those pre-computed numbers are exact; do not recalculate "
        "your own percentages from the raw tables, and do not contradict the "
        "pre-computed numbers.\n\n"
        "Your job is synthesis, not restating rows. Specifically:\n"
        "1. Identify the 2-3 findings most likely to matter for retention or revenue, "
        "ranked by likely impact, not by the order they appear in the tables.\n"
        "2. For at least one finding, connect two different tables together (e.g. "
        "does the engagement decline concentrate in a particular segment or genre? "
        "does retention track with genre diversity or plan type?) rather than "
        "reporting each table in isolation.\n"
        "3. Flag one specific risk (something getting worse) and one specific "
        "opportunity (something working that could be leaned into), each with a number.\n"
        "4. End with ONE concrete, testable recommendation — specific enough that "
        "someone could act on it this week (not 'explore ways to improve engagement').\n\n"
        "Hard rule: never invent a number that isn't in the data given to you — no "
        "made-up projected revenue lift, no fabricated percentages, no 'this could "
        "increase X by Y%' unless Y came from the tables/metrics provided. If you "
        "want to describe expected impact, describe the mechanism (why it should "
        "help) without a fabricated magnitude.\n\n"
        "Format: short bullet points, no filler sentences, no restating what a table "
        "'shows' without saying why it matters."
    )

    user_prompt = (
        f"Pre-computed, verified metrics (use these numbers as-is):\n{derived_metrics_text}\n\n"
        f"Raw query result tables (for context/detail only):\n\n{results_text}"
    )

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=700,
    )
    return resp.choices[0].message.content


def main():
    load_env_file()
    if not os.environ.get("GROQ_API_KEY"):
        raise SystemExit(
            "GROQ_API_KEY not set. Put it in a .env file next to this script "
            "or export it: export GROQ_API_KEY=your_key_here"
        )

    print("Running SQL analysis queries...")
    results = run_queries()
    prompt_text = format_results_as_plain_text(results, row_limit=10)
    report_tables = format_results_as_markdown(results, row_limit=15)
    derived_metrics_text = compute_derived_metrics(results)

    print("Sending results to Groq for AI-generated insights summary...")
    summary = get_ai_summary(prompt_text, derived_metrics_text)

    report = (
        f"# Spotify Product Analytics — Insights Report\n"
        f"_Generated {datetime.now().isoformat(timespec='seconds')}_\n\n"
        f"## AI-Generated Summary\n\n{summary}\n\n"
        f"---\n\n## Verified Metrics (computed in Python, not by the LLM)\n\n{derived_metrics_text}\n\n"
        f"---\n\n## Raw Query Results\n\n{report_tables}"
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport written to {OUTPUT_PATH}\n")
    print("=" * 60)
    print(summary)
    print("=" * 60)


if __name__ == "__main__":
    main()
