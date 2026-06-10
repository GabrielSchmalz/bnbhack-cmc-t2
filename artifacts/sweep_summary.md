# Sweep summary — plan Task 2.4 (pre-registered pipeline)

- variants swept: 36 (PR-8 denominator)
- null draws per (taxonomy, fold): 1000 (seed base 17, common random shuffles)
- window: 2025-04-03 00:00:00 .. 2026-06-09 20:00:00 (2598 bars)

## Taxonomy globals

| taxonomy | embargo E (bars) | honest_N (pooled OOS episodes) | per-fold OOS bars | per-fold OOS episodes | HODL pooled-OOS Sharpe @10bps | HODL pooled-OOS net @10bps |
|---|---|---|---|---|---|---|
| TA | 42 | 250 | F1:324, F2:330, F3:312, F4:378 | F1:54, F2:71, F3:50, F4:75 | -2.10 | -0.4590 |
| TB | 42 | 105 | F1:324, F2:330, F3:312, F4:378 | F1:11, F2:32, F3:19, F4:43 | -2.10 | -0.4590 |
| TC | 42 | 225 | F1:324, F2:330, F3:312, F4:378 | F1:52, F2:48, F3:60, F4:65 | -2.10 | -0.4590 |

## Top 15 by rank key (mean per-fold TRAIN Sharpe @10 bps RT, PR-7)

| # | id | family | tax | rank_key | OOS Sharpe | OOS net | OOS maxDD | null_p95 | unguarded OOS Sharpe | top5 net | gate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | DIR-TC-H10-short_crowded_long-0.5 | direction | TC | 1.10 | 0.44 | 0.0201 | 0.047 | 1.63 | 0.44 | -0.0625 | fail: null_pass,top5_pass,ladder_pass |
| 2 | DIR-TC-H10-short_crowded_long-1.0 | direction | TC | 1.10 | 0.44 | 0.0364 | 0.092 | 1.63 | 0.44 | -0.1240 | fail: null_pass,top5_pass,ladder_pass |
| 3 | RISK-TC-ladder-0.5_0_1_0.5 | risk | TC | 0.97 | -1.49 | -0.2551 | 0.299 | -1.02 | -1.47 | -0.3162 | fail: beats_flat,null_pass,top5_pass,ladder_pass |
| 4 | DIR-TC-H8-fade_pos_extreme_only-0.5 | direction | TC | 0.96 | 2.38 | 0.0756 | 0.021 | 2.26 | 2.38 | -0.0103 | fail: top5_pass |
| 5 | DIR-TC-H8-fade_pos_extreme_only-1.0 | direction | TC | 0.96 | 2.38 | 0.1550 | 0.042 | 2.26 | 2.38 | -0.0213 | fail: top5_pass |
| 6 | RISK-TC-ladder-1_0_1_0.5 | risk | TC | 0.92 | -1.46 | -0.3467 | 0.367 | -1.32 | -1.53 | -0.4371 | fail: beats_flat,null_pass,top5_pass,ladder_pass |
| 7 | RISK-TA-ladder-1_1_0 | risk | TA | 0.83 | -2.79 | -0.4232 | 0.440 | -0.67 | -2.79 | -0.5226 | fail: beats_flat,beats_hodl,null_pass,top5_pass,ladder_pass |
| 8 | RISK-TC-ladder-1_0.25_1_1 | risk | TC | 0.82 | -1.79 | -0.4028 | 0.424 | -1.57 | -1.72 | -0.4028 | fail: beats_flat,null_pass,top5_pass,ladder_pass |
| 9 | DIR-TC-H7-carry_fade_extremes-0.5 | direction | TC | 0.80 | 1.42 | 0.0493 | 0.039 | 2.16 | 1.42 | -0.0345 | fail: null_pass,top5_pass |
| 10 | DIR-TC-H7-carry_fade_extremes-1.0 | direction | TC | 0.80 | 1.42 | 0.0990 | 0.077 | 2.16 | 1.42 | -0.0688 | fail: null_pass,top5_pass |
| 11 | RISK-TC-ladder-1_0_0.5_0 | risk | TC | 0.51 | -1.74 | -0.3497 | 0.364 | -1.16 | -1.75 | -0.5081 | fail: beats_flat,null_pass,top5_pass,ladder_pass |
| 12 | DIR-TB-H5-fade_stress_only-0.5 | direction | TB | 0.42 | -1.49 | -0.1623 | 0.196 | 1.53 | -1.33 | -0.2649 | fail: beats_flat,null_pass,top5_pass,ladder_pass |
| 13 | DIR-TB-H5-fade_stress_only-1.0 | direction | TB | 0.40 | -1.58 | -0.3047 | 0.357 | 1.53 | -1.33 | -0.4636 | fail: beats_flat,null_pass,top5_pass,ladder_pass |
| 14 | RISK-TA-ladder-1_0.5_0 | risk | TA | 0.35 | -3.09 | -0.3266 | 0.340 | -0.49 | -3.04 | -0.4034 | fail: beats_flat,beats_hodl,null_pass,top5_pass,ladder_pass |
| 15 | RISK-TA-ladder-0.5_0.25_0 | risk | TA | 0.35 | -3.04 | -0.1745 | 0.183 | -0.49 | -3.04 | -0.2199 | fail: beats_flat,beats_hodl,null_pass,top5_pass,ladder_pass |

## Survivors (gate passes)

- none — R-NULL branch (PR-10)

## R3 disclosure

- variants swept: 36
- gate passes: 0
- expected pass-rate of the null clause under the shuffle null: 0.0500 (~0.05 by construction)
- FULL-gate pass rate over 200 null draws of the top train-ranked variant (DIR-TC-H10-short_crowded_long-0.5): 0.0150

_Wall time: 283.7 s._
