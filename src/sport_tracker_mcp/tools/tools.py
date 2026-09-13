import logging
from typing import Any

from ..client.client import SportsTrackerClient, SportsTrackerNotFoundError
from ..formatting import calculate_cutoff_ms
from ..models import (
    RecentActivitiesSummary,
    SocialFeedItem,
    TrainingLoadAndRecovery,
    TrainingSummary,
    UserStats,
    VO2MaxHistory,
    WorkoutDetail,
    WorkoutSummary,
)

logger = logging.getLogger(__name__)

client = SportsTrackerClient()


async def _fetch_workouts_for_days(
    days: int, now_ts: float | None = None, max_workouts: int = 5000
) -> list[dict[str, Any]]:
    """Fetch workouts going back `days` days from now_ts (or current time).

    Paginates through the API (newest to oldest) until workouts predate the window,
    preventing silent truncation for high-volume athletes on wider windows.
    """
    cutoff_ms = calculate_cutoff_ms(days, now_ts)

    page_size = 50
    offset = 0
    workouts_in_window: list[dict[str, Any]] = []

    while True:
        batch = await client.get_workouts(limit=page_size, offset=offset)
        if not batch:
            break

        reached_older_workout = False
        for w in batch:
            if not isinstance(w, dict):
                continue
            start_ms = w.get("startTime")
            if start_ms is None:
                continue
            if float(start_ms) >= cutoff_ms:
                workouts_in_window.append(w)
            else:
                reached_older_workout = True
                break

        if reached_older_workout or len(batch) < page_size:
            break

        offset += page_size
        if offset >= max_workouts:
            logger.warning(
                "Workout pagination reached safety limit of %d workouts for %d-day window; results may be truncated",
                max_workouts,
                days,
            )
            break

    return workouts_in_window


async def get_recent_workouts(
    limit: int = 10, imperial: bool = False
) -> list[WorkoutSummary]:
    """Get recent workouts with formatted distance, duration, pace, and HR."""
    raw_workouts = await client.get_workouts(limit=limit)
    summaries: list[WorkoutSummary] = []
    for w in raw_workouts:
        if isinstance(w, dict):
            item = WorkoutSummary.from_api(w, imperial=imperial)
            if item is not None:
                summaries.append(item)
    return summaries


async def get_social_feed(
    limit: int = 10, imperial: bool = False
) -> list[SocialFeedItem]:
    """Get social feed items from followed athletes or community."""
    raw_items = await client.get_social_feed(limit=limit)
    if isinstance(raw_items, dict):
        for k in ("feed", "items", "entries", "workouts"):
            if k in raw_items and isinstance(raw_items[k], list):
                raw_items = raw_items[k]
                break
        else:
            raw_items = []
    return [
        SocialFeedItem.from_api(item, imperial=imperial)
        for item in raw_items
        if isinstance(item, dict)
    ]


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
    days: int = 7, imperial: bool = False, now_ts: float | None = None
) -> TrainingSummary:
    """Get aggregated training volume, distance, time, and calories across sports for the past N days."""
    raw_workouts = await _fetch_workouts_for_days(days=days, now_ts=now_ts)
    return TrainingSummary.from_workouts(
        raw_workouts, days=days, imperial=imperial, now_ts=now_ts
    )


async def get_training_load_and_recovery() -> TrainingLoadAndRecovery:
    """Get current training load, recovery hours, TSS, PTE, EPOC, and recovery status from the latest workout."""
    raw_workouts = await client.get_workouts(limit=1)
    latest = raw_workouts[0] if raw_workouts else None
    return TrainingLoadAndRecovery.from_workout(latest)


async def get_recent_activities_summary(
    days: int = 14, now_ts: float | None = None
) -> RecentActivitiesSummary:
    """Get a breakdown of activity frequency, total time spent, and last performed dates over the past N days."""
    raw_workouts = await _fetch_workouts_for_days(days=days, now_ts=now_ts)
    return RecentActivitiesSummary.from_workouts(raw_workouts, days=days, now_ts=now_ts)
