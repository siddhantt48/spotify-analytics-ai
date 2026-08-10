-- Spotify Product Analytics — schema

DROP TABLE IF EXISTS listen_events;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tracks;

CREATE TABLE tracks (
    track_id         TEXT PRIMARY KEY,
    artists          TEXT,
    album_name       TEXT,
    track_name       TEXT,
    popularity       INTEGER,
    duration_ms      INTEGER,
    explicit         TEXT,
    danceability     REAL,
    energy           REAL,
    key              INTEGER,
    loudness         REAL,
    mode             INTEGER,
    speechiness      REAL,
    acousticness     REAL,
    instrumentalness REAL,
    liveness         REAL,
    valence          REAL,
    tempo            REAL,
    time_signature   INTEGER,
    track_genre      TEXT
);

CREATE TABLE users (
    user_id          INTEGER PRIMARY KEY,
    signup_date      TEXT,
    plan_type        TEXT,
    country          TEXT,
    segment          TEXT,          -- ground-truth label used only to generate data; not used in analysis
    preferred_genres TEXT
);

CREATE TABLE listen_events (
    event_id         INTEGER PRIMARY KEY,
    user_id          INTEGER REFERENCES users(user_id),
    track_id         TEXT REFERENCES tracks(track_id),
    event_timestamp  TEXT,
    week_number      INTEGER,
    ms_played        INTEGER,
    skipped          INTEGER,       -- 1 = skipped, 0 = played through
    device_type      TEXT
);

CREATE INDEX idx_events_user ON listen_events(user_id);
CREATE INDEX idx_events_track ON listen_events(track_id);
CREATE INDEX idx_events_week ON listen_events(week_number);
