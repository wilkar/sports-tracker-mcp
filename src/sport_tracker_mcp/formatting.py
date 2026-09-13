import time
from typing import Any


def format_distance(meters: float, imperial: bool = False) -> tuple[float, str]:
    if not meters or meters <= 0:
        return 0.0, "0.00 " + ("mi" if imperial else "km")
    val = (meters / 1000.0) * (0.621371192 if imperial else 1.0)
    unit = "mi" if imperial else "km"
    if val <= 100:
        return round(val, 2), f"{val:.2f} {unit}"
    elif val <= 1000:
        return round(val, 1), f"{val:.1f} {unit}"
    return float(round(val)), f"{round(val)} {unit}"


def format_speed(meters_per_sec: float, imperial: bool = False) -> tuple[float, str]:
    multiplier = 2.23693629 if imperial else 3.6
    unit = "mph" if imperial else "km/h"
    speed = round(meters_per_sec * multiplier, 1)
    return speed, f"{speed:.1f} {unit}"


def format_pace(meters_per_sec: float, imperial: bool = False) -> str:
    if meters_per_sec <= 0:
        return "00:00"
    speed = meters_per_sec * (2.23693629 if imperial else 3.6)
    pace = 60.0 / speed
    minutes = int(pace)
    seconds = int(60.0 * (pace - minutes))
    return f"{minutes}:{seconds:02d}"


def format_duration(seconds: float) -> str:
    if not seconds or seconds <= 0:
        return "00:00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def calculate_cutoff_ms(days: int, now_ts: float | None = None) -> float:
    """Calculate the epoch millisecond cutoff going back `days` days from now_ts (or current time)."""
    reference_ms = now_ts if now_ts is not None else time.time() * 1000.0
    return reference_ms - (days * 86400.0 * 1000.0)


def within_window(
    workouts: list[dict[str, Any]], days: int, now_ts: float | None = None
) -> list[dict[str, Any]]:
    """Filter workouts whose startTime (in epoch ms) is within `days` days of now_ts."""
    cutoff_ms = calculate_cutoff_ms(days, now_ts)
    valid_workouts: list[dict[str, Any]] = []
    for w in workouts:
        if not isinstance(w, dict):
            continue
        start_ms = w.get("startTime")
        if start_ms is not None and float(start_ms) >= cutoff_ms:
            valid_workouts.append(w)
    return valid_workouts
