-- =====================================================================
-- Spotify Product Analytics — core analysis queries
-- =====================================================================

-- 1. SKIP RATE BY GENRE
-- Which genres get skipped the most? (min 50 plays to avoid noisy small samples)
SELECT
    t.track_genre,
    COUNT(*)                                        AS total_plays,
    SUM(le.skipped)                                 AS skips,
    ROUND(100.0 * SUM(le.skipped) / COUNT(*), 1)     AS skip_rate_pct
FROM listen_events le
JOIN tracks t ON t.track_id = le.track_id
GROUP BY t.track_genre
HAVING COUNT(*) >= 50
ORDER BY skip_rate_pct DESC
LIMIT 15;


-- 2. WEEKLY ENGAGEMENT TREND
-- Are total listens and unique active users trending up or down?
SELECT
    week_number,
    COUNT(*)                          AS total_plays,
    COUNT(DISTINCT user_id)           AS active_users,
    ROUND(100.0 * SUM(skipped) / COUNT(*), 1) AS skip_rate_pct
FROM listen_events
GROUP BY week_number
ORDER BY week_number;


-- 3. WEEK-OVER-WEEK RETENTION
-- Of the users active in week N, what % came back in week N+1?
WITH weekly_users AS (
    SELECT DISTINCT user_id, week_number
    FROM listen_events
)
SELECT
    a.week_number                                   AS week,
    COUNT(DISTINCT a.user_id)                        AS active_this_week,
    COUNT(DISTINCT b.user_id)                        AS retained_next_week,
    ROUND(100.0 * COUNT(DISTINCT b.user_id) / COUNT(DISTINCT a.user_id), 1) AS retention_pct
FROM weekly_users a
LEFT JOIN weekly_users b
    ON a.user_id = b.user_id AND b.week_number = a.week_number + 1
GROUP BY a.week_number
ORDER BY a.week_number;


-- 4. POWER USER SEGMENTATION (window functions)
-- Rank users into quartiles by total listening volume, using NTILE.
WITH user_totals AS (
    SELECT
        user_id,
        COUNT(*)                                   AS total_plays,
        SUM(CASE WHEN skipped = 0 THEN 1 ELSE 0 END) AS completed_plays,
        ROUND(100.0 * SUM(skipped) / COUNT(*), 1)  AS skip_rate_pct
    FROM listen_events
    GROUP BY user_id
),
ranked AS (
    SELECT
        *,
        NTILE(4) OVER (ORDER BY total_plays DESC) AS engagement_quartile
    FROM user_totals
)
SELECT
    engagement_quartile,
    COUNT(*)                       AS num_users,
    ROUND(AVG(total_plays), 1)     AS avg_plays,
    ROUND(AVG(skip_rate_pct), 1)   AS avg_skip_rate_pct
FROM ranked
GROUP BY engagement_quartile
ORDER BY engagement_quartile;


-- 5. GENRE DIVERSITY PER USER
-- Do more "engaged" users listen to a wider variety of genres, or stick to fewer?
WITH user_diversity AS (
    SELECT
        le.user_id,
        COUNT(*)                              AS total_plays,
        COUNT(DISTINCT t.track_genre)         AS distinct_genres
    FROM listen_events le
    JOIN tracks t ON t.track_id = le.track_id
    GROUP BY le.user_id
)
SELECT
    CASE
        WHEN total_plays >= 100 THEN 'high_volume'
        WHEN total_plays >= 30  THEN 'mid_volume'
        ELSE 'low_volume'
    END AS volume_bucket,
    COUNT(*)                              AS num_users,
    ROUND(AVG(distinct_genres), 1)        AS avg_distinct_genres,
    ROUND(AVG(total_plays), 1)            AS avg_plays
FROM user_diversity
GROUP BY volume_bucket
ORDER BY avg_plays DESC;


-- 6. TOP TRACKS BY COMPLETION (not just raw popularity score)
-- Tracks with the highest "actually listened through" rate, min 20 plays.
SELECT
    t.track_name,
    t.artists,
    t.track_genre,
    COUNT(*)                                      AS plays,
    ROUND(100.0 * SUM(CASE WHEN le.skipped = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS completion_rate_pct
FROM listen_events le
JOIN tracks t ON t.track_id = le.track_id
GROUP BY t.track_id
HAVING COUNT(*) >= 5
ORDER BY completion_rate_pct DESC, plays DESC
LIMIT 15;


-- 7. PLAN TYPE COMPARISON
-- Do premium users behave differently from free users?
SELECT
    u.plan_type,
    COUNT(DISTINCT le.user_id)                     AS users,
    COUNT(*)                                       AS total_plays,
    ROUND(1.0 * COUNT(*) / COUNT(DISTINCT le.user_id), 1) AS avg_plays_per_user,
    ROUND(100.0 * SUM(le.skipped) / COUNT(*), 1)   AS skip_rate_pct
FROM listen_events le
JOIN users u ON u.user_id = le.user_id
GROUP BY u.plan_type;
