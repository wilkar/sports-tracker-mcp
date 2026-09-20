import time
from typing import Any

from .client import SportsTrackerClient, SportsTrackerNotFoundError
from .models import (
    RecentActivitiesSummary,
    SocialFeedItem,
    TrainingLoadAndRecovery,
    TrainingSummary,
    UserStats,
    VO2MaxHistory,
    WorkoutDetail,
    WorkoutSummary,
)

# Module-level client singleton.
# Design note: This instance is initialized at import time using environment variables
# resolved by config.py. In standard stdio MCP operation, the parent client (e.g. Claude
# Desktop, Cursor) sets the process environment before launching this server subprocess.
# Runtime modifications to os.environ made after import will not affect this instance;
# tests and callers requiring custom configurations should monkeypatch `tools.client`
# or instantiate SportsTrackerClient explicitly.
client = SportsTrackerClient()


async def _fetch_workouts_for_days(days: int) -> list[dict[str, Any]]:
    """Fetch workouts going back `days` days from current time.

    Paginates through the API (newest to oldest) until workouts predate the window.
    """
    cutoff_ms = (time.time() - (days * 86400.0)) * 1000.0

    page_size = 50
    offset = 0
    workouts_in_window: list[dict[str, Any]] = []

    while True:
        batch = await client.get_workouts(limit=page_size, offset=offset)
        if not batch:
            break

        reached_older_workout = False
        for w in batch:
            start_ms = w.get("startTime")
            if start_ms is None:
                continue
            try:
                start_ts = float(start_ms)
            except (ValueError, TypeError):
                continue

            if start_ts >= cutoff_ms:
                workouts_in_window.append(w)
            else:
                reached_older_workout = True
                break

        if reached_older_workout or len(batch) < page_size:
            break

        offset += page_size

    return workouts_in_window


def _normalize_limit(limit: int | str | None, default: int = 10) -> int:
    """Normalize limit to an int (0 represents 'all')."""
    if limit is None:
        return default
    if isinstance(limit, str):
        s = limit.strip().lower()
        if s in ("all", "0"):
            return 0
        try:
            return max(0, int(s))
        except ValueError:
            return default
    return max(0, int(limit))


def _sport_matches(filter_sport: str, workout_sport: str) -> bool:
    f = filter_sport.strip().lower()
    s = workout_sport.strip().lower()
    if not f:
        return True
    if f == s:
        return True
    f_clean = f.replace("-", " ").replace("_", " ")
    s_clean = s.replace("-", " ").replace("_", " ")
    if f_clean == s_clean or f_clean in s_clean:
        return True
    aliases: dict[str, list[str]] = {
        "cycle": ["cycling", "indoor cycling", "mountain biking"],
        "bike": ["cycling", "indoor cycling", "mountain biking"],
        "biking": ["cycling", "indoor cycling", "mountain biking"],
        "run": ["running", "trail running", "treadmill"],
        "walk": ["walking", "nordic walking"],
        "swim": ["pool swimming", "openwater swimming"],
        "ski": [
            "cross-country skiing",
            "alpine skiing",
            "ski touring",
            "roller skiing",
        ],
        "weights": ["gym", "outdoor gym", "circuit training"],
    }
    for alias, targets in aliases.items():
        if f == alias and any(t in s for t in targets):
            return True
    return False


async def get_recent_workouts(
    limit: int | str = 10, imperial: bool = False, sport: str | None = None
) -> list[WorkoutSummary]:
    """Get recent workouts with formatted distance, duration, pace, and HR.

    Args:
        limit: Maximum number of recent workouts to retrieve (default: 10, or 'all').
        imperial: Whether to format units in imperial (miles, ft) instead of metric.
        sport: Optional sport name to filter by (e.g. 'running', 'cycling', 'walking', 'gym').
    """
    norm = _normalize_limit(limit)
    target = norm if norm > 0 else 100
    page_size = min(target, 100) if not sport else 100
    offset = 0
    summaries: list[WorkoutSummary] = []

    while len(summaries) < target:
        batch = await client.get_workouts(limit=page_size, offset=offset)
        if not batch:
            break
        for raw in batch:
            item = WorkoutSummary.from_api(raw, imperial=imperial)
            if item is not None and (not sport or _sport_matches(sport, item.sport)):
                summaries.append(item)
                if len(summaries) >= target:
                    break
        if len(batch) < page_size:
            break
        offset += len(batch)

    return summaries


async def get_social_feed(
    limit: int = 10, imperial: bool = False
) -> list[SocialFeedItem]:
    """Get social feed items from followed athletes or community."""
    raw_items = await client.get_social_feed(limit=limit)
    return [SocialFeedItem.from_api(item, imperial=imperial) for item in raw_items]


async def get_workout_details(
    workout_key: str, imperial: bool = False
) -> WorkoutDetail:
    """Get detailed workout metrics including ascent, descent, HR zones, gear, and Suunto extensions."""
    raw_detail = await client.get_workout_details(workout_key=workout_key)
    detail = WorkoutDetail.from_api(raw_detail, imperial=imperial)
    if detail is None:
        raise SportsTrackerNotFoundError(
            f"Workout not found or malformed: {workout_key}"
        )
    return detail


async def get_user_stats(
    username: str | None = None, imperial: bool = False
) -> UserStats:
    """Get lifetime totals and per-sport breakdown stats for the logged-in user or specified username."""
    raw_stats = await client.get_user_stats(username=username)
    return UserStats.from_api(raw_stats, imperial=imperial)


async def get_vo2_max_history(limit: int = 20) -> VO2MaxHistory:
    """Get VO2Max and fitness age history extracted from recent workouts."""
    raw_workouts = await client.get_workouts(limit=limit)
    return VO2MaxHistory.from_workouts(raw_workouts)


async def get_training_summary(
    days: int = 7, imperial: bool = False
) -> TrainingSummary:
    """Get aggregated training volume, distance, time, and calories across sports for the past N days."""
    raw_workouts = await _fetch_workouts_for_days(days=days)
    return TrainingSummary.from_workouts(raw_workouts, days=days, imperial=imperial)


async def get_training_load_and_recovery() -> TrainingLoadAndRecovery:
    """Get current training load, recovery hours, TSS, PTE, EPOC, and recovery status from the latest workout."""
    raw_workouts = await client.get_workouts(limit=1)
    latest = raw_workouts[0] if raw_workouts else None
    return TrainingLoadAndRecovery.from_workout(latest)


async def get_recent_activities_summary(
    days: int = 14,
) -> RecentActivitiesSummary:
    """Get a breakdown of activity frequency, total time spent, and last performed dates over the past N days.

    Args:
        days: Number of past days to aggregate activity summary for (default: 14).
    """
    raw_workouts = await _fetch_workouts_for_days(days=days)
    return RecentActivitiesSummary.from_workouts(raw_workouts, days=days)
