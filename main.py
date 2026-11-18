"""Forecast GTA VI's launch-day Twitch viewers hour by hour (make.fun gta6-twitch-ccu-forecast-01).

Method: magnitude-matched median-normal ratio forecast.

The case hands the program everything it needs: hour 1's print (p1) and the
hourly Twitch histories of dozens of past big game launches ("comparables").
A launch day has a shape: viewers dip in the small UTC hours, then climb as
the world wakes up and the US evening arrives. That shape is stable when
measured as log-ratios to hour 1, but only among launches of a similar size:
a launch whose hour 1 drew 200 viewers can grow 100x by evening, while a
launch whose hour 1 drew 500,000 viewers cannot. So for each hour h = 2..24:

  1. Take as donors the comparables whose release day is complete (all 24
     hourly prints present and positive) and whose hour-1 print is within
     10x of this case's hour-1 print, in either direction. If fewer than
     three donors qualify, take the three nearest by |log(hour1 / p1)|.
  2. For each donor, form the log-ratio r = ln(viewers_h / viewers_1),
     clipped to [-1.2, +1.8] so one freak launch cannot drag the spread.
  3. Centre = the median of the clipped ratios (robust to the right tail);
     spread = their sample standard deviation.
  4. Quantiles: q_tau(h) = p1 * exp(centre + z_tau * spread), with
     z = [-1.645, -0.674, 0, 0.674, 1.645] for the 5/25/50/75/95% levels,
     rounded half-up to 2 decimals.

Nothing is fetched at run time: the program reads only its case file and
uses only the Python standard library. It is deterministic (donors sorted by
name, no randomness, no clock reads), so two runs write identical bytes.

Validation (leave-one-out over the 37 complete comparables in the kit's
practice cases, scored by the contest's own mean pinball loss on the log
scale, targets restricted to big launches with hour-1 >= 20,000 viewers,
the population GTA VI belongs to):
  house baseline (persistence):            ~0.32-0.35
  this model:                                ~0.25
  90% coverage:                              ~0.90 (honest)
The model's centre and spread come only from the comparables in the case
file; no number in it was fitted to any practice launch's answer, and the
practice launches are not among the donors in a practice case.

Deliberately NOT used: the target's own pre-release hourly history (trailer
hype, not gameplay), the top-20 live streams at the checkpoint and the
categories table (hour 1's print already carries the launch's scale).
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a module
# shipped beside this file would import. (This entry is one file.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
# Log-ratio clip: one freak launch cannot drag an hour's spread.
CLIP_LO, CLIP_HI = -1.2, 1.8
# Donor magnitude window: hour-1 print within 10x of the case's, either way.
WIN_LO, WIN_HI = 0.1, 10.0
# Minimum donors; fewer than this, take the nearest by hour-1 size instead.
MIN_DONORS = 3


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as JavaScript's Math.round(x * 100) / 100 rounds it.

    A whole number comes back as an int, so json.dumps writes 1240 where
    JavaScript writes 1240 (not 1240.0).
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def release_day_series(comp: dict) -> dict:
    """{hour: viewers} for the comparable's release UTC day, hours 1..24.

    A comparable's `hourly` list runs from 14 days before its release day
    to 3 days after it; only the 24 hours of the release day itself count.
    """
    day_start = parse_ts(comp["day_start"])
    out = {}
    for point in comp["hourly"]:
        hour = int((parse_ts(point["from"]) - day_start).total_seconds() // 3600) + 1
        if 1 <= hour <= 24 and hour not in out:
            out[hour] = point["viewers"]
    return out


def median(sorted_values: list) -> float:
    n = len(sorted_values)
    mid = n // 2
    if n % 2:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])

    # Donors: comparables with a complete, positive release day. The
    # pre-release history of the target's own category (day_start at the
    # trailer premiere, no release day) drops out here on its own.
    donors = []
    for comp in case["comparables"]:
        series = release_day_series(comp)
        if len(series) == 24 and series.get(1, 0) and all(v > 0 for v in series.values()):
            donors.append((comp["name"], series))
    donors.sort(key=lambda d: d[0])
    if not donors:
        raise ValueError(f"{name} has no comparable with a complete release day")

    # Magnitude-matched pool, with a nearest-by-size fallback.
    pool = [d for d in donors if WIN_LO <= d[1][1] / p1 <= WIN_HI]
    if len(pool) < MIN_DONORS:
        pool = sorted(donors, key=lambda d: abs(math.log(d[1][1] / p1)))[:MIN_DONORS]

    hours = []
    for row in case["forecast"]:
        h = row["hour"]
        ratios = []
        for _name, series in pool:
            r = math.log(series[h] / series[1])
            ratios.append(max(CLIP_LO, min(CLIP_HI, r)))
        ratios.sort()
        centre = median(ratios)
        mean = sum(ratios) / len(ratios)
        spread = (sum((r - mean) ** 2 for r in ratios) / max(len(ratios) - 1, 1)) ** 0.5
        qs = [round2(max(1.0, min(1e9, p1 * math.exp(centre + z * spread)))) for z in Z]
        hours.append({"hour": h, "q": qs})
    return {"hours": hours}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
