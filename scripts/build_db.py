"""Loads tracks/users/listen_events CSVs into a SQLite database using schema.sql."""
import sqlite3
import pandas as pd
import os

BASE = "/sessions/loving-funny-tesla/mnt/outputs/spotify-analytics-ai"
# SQLite needs proper file locking for its journal; the mounted output folder
# is a FUSE mount that doesn't support this well, so build the DB on local
# disk first and copy the finished file over.
TMP_DB_PATH = "/tmp/spotify_analytics.db"
TMP_JOURNAL = "/tmp/spotify_analytics.db-journal"
FINAL_DB_PATH = f"{BASE}/spotify_analytics.sqlite"

for p in [TMP_DB_PATH, TMP_JOURNAL]:
    if os.path.exists(p):
        os.remove(p)

conn = sqlite3.connect(TMP_DB_PATH)
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

import shutil
shutil.copyfile(TMP_DB_PATH, FINAL_DB_PATH)
print(f"Database built and copied to {FINAL_DB_PATH}")
