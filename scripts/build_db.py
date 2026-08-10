"""Loads tracks/users/listen_events CSVs into a SQLite database using schema.sql."""
import sqlite3
import pandas as pd
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = f"{BASE}/spotify_analytics.sqlite"

for p in [DB_PATH, f"{DB_PATH}-journal"]:
    if os.path.exists(p):
        os.remove(p)

conn = sqlite3.connect(DB_PATH)
with open(f"{BASE}/sql/schema.sql") as f:
    conn.executescript(f.read())

tracks = pd.read_csv(f"{BASE}/data/tracks.csv")
users = pd.read_csv(f"{BASE}/data/users.csv")
events = pd.read_csv(f"{BASE}/data/listen_events.csv")

tracks.to_sql("tracks", conn, if_exists="append", index=False)
users.to_sql("users", conn, if_exists="append", index=False)
events.to_sql("listen_events", conn, if_exists="append", index=False)

conn.commit()

cur = conn.cursor()
for t in ["tracks", "users", "listen_events"]:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t}: {cur.fetchone()[0]} rows")

conn.close()

print(f"Database built at {DB_PATH}")
