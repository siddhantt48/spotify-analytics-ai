# Spotify Product Analytics — Insights Report
_Generated 2026-07-26T01:43:59_

## AI-Generated Summary

* Key findings:
  * The most engaged quartile (Q1) plays 7.2x more than the least engaged quartile (Q4), with nearly identical skip rates, indicating a significant opportunity to increase overall engagement by targeting Q4 users.
  * Free-plan users average 104.6 plays/user vs 99.1 for premium, with similar skip rates, suggesting that the free plan may be a more effective way to drive engagement.
  * The decline in total plays (-17.4%) and active users (-20.7%) from week 1 to week 8 may be concentrated in specific genres or user segments, which could be mitigated by targeted interventions.
* Connecting tables: The high skip rates in certain genres (e.g. classical, trance) may be related to the low engagement levels in the Q4 user segment, as these users may be more likely to skip tracks in genres they are less familiar with.
* Risk: The significant decline in total plays and active users over the 8-week period (-17.4% and -20.7%, respectively) poses a risk to revenue and retention.
* Opportunity: The high engagement levels of free-plan users (104.6 plays/user) present an opportunity to increase overall engagement and potentially drive revenue through targeted promotions or upselling.
* Recommendation: Offer a limited-time promotion to Q4 users, providing them with a curated playlist of popular tracks in genres with low skip rates (e.g. reggaeton), to increase their engagement and encourage them to upgrade to a premium plan.

---

## Verified Metrics (computed in Python, not by the LLM)

- Total plays changed -17.4% from week 1 to week 8 (8444 -> 6978).
- Active users changed -20.7% from week 1 to week 8 (575 -> 456).
- Retention ranged from 91.3% (week 5) to 97.8% (week 7).
- Among the highest-skip genres (min 50 plays), rates range from classical at 28.0% down to spanish at 24.1% (3.9-point spread) — these are still all above-average skip rates, not a 'best' genre.
- The most engaged quartile (Q1) plays 7.2x more than the least engaged quartile (Q4): 223.7 vs 31.0 avg plays/user, with nearly identical skip rates (20.5% vs 20.8%).
- Free-plan users average 104.6 plays/user vs 99.1 for premium, with skip rates of 20.3% (free) vs 20.8% (premium).

---

## Raw Query Results

### SKIP RATE BY GENRE
| track_genre | total_plays | skips | skip_rate_pct |
|---|---|---|---|
| classical | 375 | 105 | 28.0 |
| trance | 398 | 108 | 27.1 |
| indie | 320 | 85 | 26.6 |
| world-music | 404 | 107 | 26.5 |
| minimal-techno | 511 | 134 | 26.2 |
| singer-songwriter | 464 | 121 | 26.1 |
| emo | 401 | 104 | 25.9 |
| soul | 275 | 71 | 25.8 |
| disco | 409 | 104 | 25.4 |
| death-metal | 341 | 86 | 25.2 |
| honky-tonk | 518 | 129 | 24.9 |
| disney | 376 | 92 | 24.5 |
| pop-film | 627 | 153 | 24.4 |
| detroit-techno | 786 | 190 | 24.2 |
| spanish | 522 | 126 | 24.1 |

### WEEKLY ENGAGEMENT TREND
| week_number | total_plays | active_users | skip_rate_pct |
|---|---|---|---|
| 1 | 8444 | 575 | 20.5 |
| 2 | 8512 | 571 | 20.7 |
| 3 | 8150 | 546 | 20.5 |
| 4 | 7884 | 533 | 20.2 |
| 5 | 7609 | 505 | 19.7 |
| 6 | 7118 | 481 | 20.6 |
| 7 | 6917 | 451 | 20.7 |
| 8 | 6978 | 456 | 20.8 |

### WEEK-OVER-WEEK RETENTION
| week | active_this_week | retained_next_week | retention_pct |
|---|---|---|---|
| 1 | 575 | 557 | 96.9 |
| 2 | 571 | 531 | 93.0 |
| 3 | 546 | 508 | 93.0 |
| 4 | 533 | 493 | 92.5 |
| 5 | 505 | 461 | 91.3 |
| 6 | 481 | 439 | 91.3 |
| 7 | 451 | 441 | 97.8 |
| 8 | 456 | 0 | 0.0 |

### POWER USER SEGMENTATION (window functions)
| engagement_quartile | num_users | avg_plays | avg_skip_rate_pct |
|---|---|---|---|
| 1 | 150 | 223.7 | 20.5 |
| 2 | 150 | 83.7 | 19.5 |
| 3 | 150 | 72.4 | 21.0 |
| 4 | 150 | 31.0 | 20.8 |

### GENRE DIVERSITY PER USER
| volume_bucket | num_users | avg_distinct_genres | avg_plays |
|---|---|---|---|
| high_volume | 109 | 59.3 | 272.5 |
| mid_volume | 413 | 22.9 | 74.7 |
| low_volume | 78 | 6.9 | 13.7 |

### TOP TRACKS BY COMPLETION (not just raw popularity score)
| track_name | artists | track_genre | plays | completion_rate_pct |
|---|---|---|---|---|
| Red Red Wine | UB40 | reggae | 9 | 100.0 |
| Fiel | Los Legendarios;Wisin;Jhay Cortez | reggaeton | 9 | 100.0 |
| Carmelina | Merengues Dorados | reggaeton | 8 | 100.0 |
| Yo Se Que Tu | Marcianeke | reggaeton | 8 | 100.0 |
| Light On | Maggie Rogers | indie-pop | 7 | 100.0 |
| Hey DJ | CNCO;Yandel | reggaeton | 7 | 100.0 |
| Quédate | Grupo C4 | reggaeton | 7 | 100.0 |
| Molly | ITHAN NY;King Savagge;Rich Melody | reggaeton | 7 | 100.0 |
| Hey Ma (with J Balvin & Pitbull feat. Camila Cabello) | J Balvin;Pitbull;Camila Cabello | reggaeton | 7 | 100.0 |
| September Song | JP Cooper | house | 7 | 100.0 |
| Brother | Kodaline | rock | 7 | 100.0 |
| Una Vaina Loca | Fuego | reggaeton | 7 | 100.0 |
| Pretend | CNCO | reggaeton | 7 | 100.0 |
| Tacones Rojos | Sebastian Yatra | reggaeton | 6 | 100.0 |
| Coroné | Flyboiz;MC Davo | reggaeton | 6 | 100.0 |

### PLAN TYPE COMPARISON
| plan_type | users | total_plays | avg_plays_per_user | skip_rate_pct |
|---|---|---|---|---|
| free | 394 | 41198 | 104.6 | 20.3 |
| premium | 206 | 20414 | 99.1 | 20.8 |
