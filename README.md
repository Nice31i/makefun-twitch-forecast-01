# makefun-twitch-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Nice31i/makefun-twitch-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Nice31i/makefun-twitch-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecast how many people will be watching Grand Theft Auto VI live on Twitch in each hour of its release day (2026-11-19 UTC), as five quantiles an hour, from hour 1's print and the hourly histories of past big game launches.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` (Python 3.13, standard library only) reads every `*.in` case in the input directory and writes one `*.out` forecast per case: 23 rows, hours 2–24, each five quantiles at the 5/25/50/75/95% levels. Deterministic — two runs write identical bytes — and well inside the 8-second limit.

## Method

Magnitude-matched median-normal ratio forecast. A launch day has a shape — viewers dip in the small UTC hours, then climb as the world wakes up and the US evening arrives — and that shape is stable when measured as log-ratios to hour 1, but only among launches of a similar size. For each hour:

1. Donors are the comparables in the case file whose release day is complete (all 24 hourly prints present and positive) and whose hour-1 print is within 10× of this case's hour-1 print, either way (fewer than three donors: the three nearest by hour-1 size).
2. For each donor, the log-ratio ln(viewers_h / viewers_1), clipped to [−1.2, +1.8].
3. Centre = the median of the clipped ratios; spread = their sample standard deviation.
4. Quantiles: q = p1 · exp(centre + z · spread), z = [−1.645, −0.674, 0, 0.674, 1.645].

No network, no model call, no data fetched at run time — everything comes from the case file. The target's own pre-release history (trailer hype, not gameplay), the top-20 live streams and the categories table are deliberately not used: hour 1's print already carries the launch's scale.

## Validation

Leave-one-out over the 37 complete comparables in the kit's practice cases, scored by the contest's mean pinball loss on the log scale, targets restricted to big launches (hour-1 ≥ 20,000 viewers, the population GTA VI belongs to): this model ≈ 0.25, house baseline (persistence) ≈ 0.32–0.35, 90% coverage ≈ 0.90. No number was fitted to any practice launch's answer.

---

Entered on [make.fun](https://make.fun/?ref=jolly-falcon-75&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards
