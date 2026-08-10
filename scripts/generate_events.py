"""
Generates synthetic users + listening events on top of the real Spotify
tracks dataset (Kaggle/HF: maharshipandya/spotify-tracks-dataset).

Real per-user listening history isn't public, so this simulates realistic
behavior patterns (preferred genres, skip behavior, churn) so the SQL
layer has something meaningful to analyze.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

DATA_DIR = "/sessions/loving-funny-tesla/mnt/outputs/spotify-analytics-ai/data"

tracks = pd.read_csv(f"{DATA_DIR}/tracks_raw.csv", index_col=0)
tracks = tracks.dropna(subset=["track_id", "track_genre"]).drop_duplicates(subset=["track_id"])

genres = tracks["track_genre"].unique().tolist()
print(f"Loaded {len(tracks)} tracks across {len(genres)} genres")

N_USERS = 600
WEEKS = 8
START_DATE = datetime(2026, 5, 1)
PLANS = ["free", "premium"]
COUNTRIES = ["US", "UK", "IN", "BR", "DE", "CA", "AU", "MX"]

# --- users ---
user_rows = []
# behavior segments: power / casual / churn_risk (stops listening partway through)
segments = np.random.choice(
    ["power", "casual", "churn_risk", "dormant"],
    size=N_USERS,
    p=[0.15, 0.55, 0.20, 0.10]
)

for uid in range(1, N_USERS + 1):
    signup_offset = random.randint(0, 30)  # signed up in first month
    n_pref_genres = random.randint(2, 4)
    pref_genres = random.sample(genres, n_pref_genres)
    user_rows.append({
        "user_id": uid,
        "signup_date": (START_DATE + timedelta(days=signup_offset)).date().isoformat(),
        "plan_type": np.random.choice(PLANS, p=[0.65, 0.35]),
        "country": random.choice(COUNTRIES),
        "segment": segments[uid - 1],
        "preferred_genres": "|".join(pref_genres),
    })

users_df = pd.DataFrame(user_rows)

# --- listen events ---
SEGMENT_WEEKLY_EVENTS = {"power": (25, 45), "casual": (5, 15), "churn_risk": (8, 20), "dormant": (1, 4)}
# churn_risk users stop showing up after a random week between 2 and 6
churn_week = {u: random.randint(2, 6) for u in users_df.loc[users_df.segment == "churn_risk", "user_id"]}

events = []
event_id = 1
tracks_by_genre = {g: tracks[tracks.track_genre == g] for g in genres}

for _, u in users_df.iterrows():
    uid = u.user_id
    seg = u.segment
    pref_genres = u.preferred_genres.split("|")
    lo, hi = SEGMENT_WEEKLY_EVENTS[seg]

    for week in range(WEEKS):
        if seg == "churn_risk" and week >= churn_week[uid]:
            continue  # user has churned
        if seg == "dormant" and random.random() < 0.4:
            continue  # dormant users skip weeks entirely

        n_events = random.randint(lo, hi)
        for _ in range(n_events):
            # 70% chance the track comes from a preferred genre, 30% discovery
            if random.random() < 0.7:
                g = random.choice(pref_genres)
            else:
                g = random.choice(genres)
            track = tracks_by_genre[g].sample(1).iloc[0]

            day_offset = week * 7 + random.randint(0, 6)
            ts = START_DATE + timedelta(days=day_offset, seconds=random.randint(0, 86399))

            # skip probability: higher for low-energy-match / non-preferred genre / long tracks
            base_skip_prob = 0.12 if g in pref_genres else 0.35
            base_skip_prob += 0.1 if track.duration_ms > 300000 else 0
            skipped = random.random() < min(base_skip_prob, 0.85)

            ms_played = int(track.duration_ms * random.uniform(0.05, 0.25)) if skipped \
                else int(track.duration_ms * random.uniform(0.85, 1.0))

            events.append({
                "event_id": event_id,
                "user_id": uid,
                "track_id": track.track_id,
                "event_timestamp": ts.isoformat(sep=" "),
                "week_number": week + 1,
                "ms_played": ms_played,
                "skipped": int(skipped),
                "device_type": random.choice(["mobile", "desktop", "web", "speaker"]),
            })
            event_id += 1

events_df = pd.DataFrame(events)
print(f"Generated {len(events_df)} listening events for {N_USERS} users")

users_df.to_csv(f"{DATA_DIR}/users.csv", index=False)
events_df.to_csv(f"{DATA_DIR}/listen_events.csv", index=False)
tracks.to_csv(f"{DATA_DIR}/tracks.csv", index=False)

print("Wrote users.csv, listen_events.csv, tracks.csv")
