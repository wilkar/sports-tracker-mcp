import httpx
import pytest

from sport_tracker_mcp.client.client import SportsTrackerClient
from sport_tracker_mcp.models import (
    ActivityCount,
    RecentActivitiesSummary,
    SocialFeedItem,
    SportStats,
    SportTrainingSummary,
    TrainingLoadAndRecovery,
    TrainingSummary,
    UserStats,
    VO2MaxHistory,
    VO2MaxRecord,
    WorkoutDetail,
    WorkoutSummary,
)
from sport_tracker_mcp.tools import tools
from sport_tracker_mcp.tools.tools import (
    get_recent_activities_summary,
    get_recent_workouts,
    get_social_feed,
    get_training_load_and_recovery,
    get_training_summary,
    get_user_stats,
    get_vo2_max_history,
    get_workout_details,
)
from tests.fixtures import (
    MOCK_USER_FEED_PAYLOAD,
    MOCK_USER_STATS_PAYLOAD,
    MOCK_WORKOUT_DETAILS_PAYLOAD,
    MOCK_WORKOUTS_PAYLOAD,
    sports_tracker_mock_handler,
)


@pytest.fixture(autouse=True)
def mock_sports_tracker_client(monkeypatch):
    """
    Mock the SportsTrackerClient used inside tools.py so tests don't make real network calls.
    """
    transport = httpx.MockTransport(sports_tracker_mock_handler)
    mocked_client = SportsTrackerClient(session_key="mock-key", transport=transport)
    monkeypatch.setattr(tools, "client", mocked_client)
    return mocked_client


# ============================================================================
# 1. get_recent_workouts
# ============================================================================


@pytest.mark.asyncio
async def test_get_recent_workouts():
    results = await get_recent_workouts(limit=10)

    assert isinstance(results, list)
    assert len(results) == len(MOCK_WORKOUTS_PAYLOAD)
    assert all(isinstance(w, WorkoutSummary) for w in results)

    # Workout 0 (Walking)
    w0 = results[0]
    assert w0.workout_key == MOCK_WORKOUTS_PAYLOAD[0]["workoutKey"]
    assert w0.sport == "walking"
    assert w0.duration_formatted == "01:05:07"
    assert w0.distance_formatted == "1.19 km"
    assert w0.avg_speed_formatted == "1.1 km/h"
    assert w0.avg_pace_formatted == "55:33"
    assert w0.distance_km == 1.19
    assert w0.duration_seconds == 3907.3
    assert w0.calories_kcal == 295
    assert w0.avg_hr == 91
    assert w0.max_hr == 121
    assert w0.step_count == 1270

    # Workout 1 (Gym - zero distance, no steps)
    w1 = results[1]
    assert w1.workout_key == MOCK_WORKOUTS_PAYLOAD[1]["workoutKey"]
    assert w1.sport == "gym"
    assert w1.distance_km == 0.0
    assert w1.distance_formatted == "0.00 km"
    assert w1.duration_formatted == "01:02:30"
    assert w1.avg_speed_formatted == "0.0 km/h"
    assert w1.avg_pace_formatted == "00:00"
    assert w1.calories_kcal == 637
    assert w1.avg_hr == 132
    assert w1.max_hr == 169
    assert w1.step_count is None

    # Workout 2 (Cycling)
    w2 = results[2]
    assert w2.workout_key == MOCK_WORKOUTS_PAYLOAD[2]["workoutKey"]
    assert w2.sport == "cycling"
    assert w2.distance_km == 3.19
    assert w2.distance_formatted == "3.19 km"
    assert w2.duration_formatted == "00:22:24"
    assert w2.avg_speed_formatted == "8.5 km/h"
    assert w2.avg_pace_formatted == "7:01"
    assert w2.calories_kcal == 148
    assert w2.avg_hr == 103
    assert w2.max_hr == 154
    assert w2.step_count is None


@pytest.mark.asyncio
async def test_get_recent_workouts_imperial():
    results = await get_recent_workouts(limit=1, imperial=True)
    w0 = results[0]
    assert "mi" in w0.distance_formatted
    assert "mph" in w0.avg_speed_formatted


# ============================================================================
# 2. get_social_feed
# ============================================================================


@pytest.mark.asyncio
async def test_get_social_feed():
    feed = await get_social_feed(limit=5)

    assert isinstance(feed, list)
    assert len(feed) == len(MOCK_USER_FEED_PAYLOAD)
    assert all(isinstance(item, SocialFeedItem) for item in feed)

    # Item 0 is AMBASSADOR
    item0 = feed[0]
    assert item0.feed_type == "AMBASSADOR"
    assert item0.workout_key is None
    assert item0.distance_formatted is None

    # Item 1 is WORKOUT
    item1 = feed[1]
    assert item1.feed_type == "WORKOUT"
    assert item1.username == "mock_athlete"
    assert item1.athlete_name == "Mock Athlete"
    assert item1.workout_key == "6aa6e2cc73ed6b7db03df35c"
    assert item1.sport == "walking"
    assert item1.distance_formatted == "1.19 km"
    assert item1.duration_formatted == "01:05:07"
    assert item1.avg_speed_formatted == "1.1 km/h"


# ============================================================================
# 3. get_workout_details
# ============================================================================


@pytest.mark.asyncio
async def test_get_workout_details():
    detail = await get_workout_details(workout_key="6aa51ebbb8ec551cf5e84e70")

    assert isinstance(detail, WorkoutDetail)
    assert detail.workout_key == "6aa51ebbb8ec551cf5e84e70"
    assert detail.sport == "cycling"
    assert detail.description == "Afternoon Ride"
    assert detail.distance_km == 3.19
    assert detail.distance_formatted == "3.19 km"
    assert detail.duration_formatted == "00:22:24"
    assert detail.avg_speed_formatted == "8.5 km/h"
    assert detail.max_speed_formatted == "32.4 km/h"
    assert detail.ascent_meters == 33.5
    assert detail.descent_meters == 29.9
    assert detail.calories_kcal == 148
    assert detail.avg_hr == 103
    assert detail.max_hr == 154
    assert detail.gear == "Suunto Race"


# ============================================================================
# 4. get_user_stats
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_stats():
    stats = await get_user_stats()

    assert isinstance(stats, UserStats)
    assert stats.total_distance_km == 9855.0
    assert stats.total_distance_formatted == "9855 km"
    assert stats.total_duration_hours == 3026.2
    assert stats.total_workouts == 2651
    assert stats.total_calories_kcal == 1460192
    assert stats.total_days == 1858
    assert len(stats.sports) == 4

    sports_names = [s.sport for s in stats.sports]
    assert "walking" in sports_names
    assert "gym" in sports_names
    assert "running" in sports_names
    assert "cycling" in sports_names


@pytest.mark.asyncio
async def test_get_user_stats_for_specific_user():
    stats = await get_user_stats(username="mock_athlete")
    assert isinstance(stats, UserStats)
    assert stats.total_workouts == 2651


# ============================================================================
# 5. get_vo2_max_history
# ============================================================================


@pytest.mark.asyncio
async def test_get_vo2_max_history():
    history = await get_vo2_max_history(limit=20)

    assert isinstance(history, VO2MaxHistory)
    assert len(history.records) == 1
    assert history.latest_vo2_max == 39.0
    assert history.average_vo2_max == 39.0
    assert history.latest_fitness_age == 45

    rec = history.records[0]
    assert isinstance(rec, VO2MaxRecord)
    assert rec.workout_key == "6aa6e2cc73ed6b7db03df35c"
    assert rec.sport == "walking"
    assert rec.vo2_max == 39.0
    assert rec.estimated_vo2_max == 38.9
    assert rec.fitness_age == 45
    assert rec.max_hr == 186


# ============================================================================
# 6. get_training_summary
# ============================================================================


@pytest.mark.asyncio
async def test_get_training_summary():
    summary = await get_training_summary(days=7)

    assert isinstance(summary, TrainingSummary)
    assert summary.days == 7
    assert summary.workouts_count == 3
    assert summary.total_distance_km == 4.38
    assert summary.total_distance_formatted == "4.38 km"
    assert summary.total_duration_formatted == "02:30:03"
    assert summary.total_calories_kcal == 1080
    assert len(summary.sports) == 3

    sports_dict = {s.sport: s for s in summary.sports}
    assert "walking" in sports_dict
    assert "gym" in sports_dict
    assert "cycling" in sports_dict


@pytest.mark.asyncio
async def test_get_training_summary_imperial():
    summary = await get_training_summary(days=7, imperial=True)
    assert "mi" in summary.total_distance_formatted


# ============================================================================
# 7. get_training_load_and_recovery
# ============================================================================


@pytest.mark.asyncio
async def test_get_training_load_and_recovery():
    recovery = await get_training_load_and_recovery()

    assert isinstance(recovery, TrainingLoadAndRecovery)
    assert recovery.latest_workout_key == "6aa6e2cc73ed6b7db03df35c"
    assert recovery.latest_sport == "walking"
    assert recovery.cumulative_recovery_hours == 6.8
    assert recovery.latest_workout_recovery_hours == 0.6
    assert recovery.training_stress_score == 38.6
    assert recovery.peak_training_effect == 1.3
    assert recovery.peak_epoc == 3.5
    assert recovery.impact_tag == "IMPACT_LONG_AEROBIC_BASE"
    assert recovery.recovery_status == "Ready for Training"


@pytest.mark.asyncio
async def test_get_training_load_and_recovery_no_workouts(monkeypatch):
    # Mock client.get_workouts to return an empty list
    async def mock_empty_workouts(*args, **kwargs):
        return []

    monkeypatch.setattr(tools.client, "get_workouts", mock_empty_workouts)
    recovery = await get_training_load_and_recovery()

    assert isinstance(recovery, TrainingLoadAndRecovery)
    assert recovery.cumulative_recovery_hours == 0.0
    assert recovery.recovery_status == "Fully Recovered"


# ============================================================================
# 8. get_recent_activities_summary
# ============================================================================


@pytest.mark.asyncio
async def test_get_recent_activities_summary():
    summary = await get_recent_activities_summary(days=14)

    assert isinstance(summary, RecentActivitiesSummary)
    assert summary.days == 14
    assert summary.total_sessions == 3
    assert len(summary.activities) == 3

    activity_map = {a.sport: a for a in summary.activities}
    assert "walking" in activity_map
    assert "gym" in activity_map
    assert "cycling" in activity_map
    assert activity_map["walking"].count == 1
    assert activity_map["gym"].count == 1
    assert activity_map["cycling"].count == 1


# ============================================================================
# 9. Regression Tests for Bug Fixes
# ============================================================================


@pytest.mark.asyncio
async def test_get_social_feed_dict_payload(monkeypatch):
    """Bug 1: get_social_feed must handle dict payload without crashing on string keys."""

    async def mock_dict_feed(*args, **kwargs):
        return {
            "feed": [
                {"feedType": "WORKOUT", "workoutKey": "k1", "startTime": 1789317924710}
            ]
        }

    monkeypatch.setattr(tools.client, "get_social_feed", mock_dict_feed)
    feed = await get_social_feed(limit=5)
    assert len(feed) == 1
    assert feed[0].workout_key == "k1"


@pytest.mark.asyncio
async def test_get_recent_workouts_malformed_skipped(monkeypatch):
    """Bug 4: get_recent_workouts must skip malformed entries without KeyError."""

    async def mock_malformed_workouts(*args, **kwargs):
        return [
            {"workoutKey": "k1", "startTime": 1789317924710, "activityId": 1},
            {"bad": "entry", "no_key": 123},
            "not a dict",
        ]

    monkeypatch.setattr(tools.client, "get_workouts", mock_malformed_workouts)
    results = await get_recent_workouts(limit=10)
    assert len(results) == 1
    assert results[0].workout_key == "k1"


@pytest.mark.asyncio
async def test_days_filtering_training_summary():
    """Bug 2 & 5: get_training_summary actually filters by days window."""
    # Workout 0: 1789317924710 (~0.6h before ref)
    # Workout 1: 1789295335480 (~6.8h before ref)
    # Workout 2: 1789204574340 (~32h before ref)
    ref_ts = 1789320000000.0

    # days=1: cutoff is 24 hours prior -> Workout 0 and 1 are within window, Workout 2 is not
    sum_1d = await get_training_summary(days=1, now_ts=ref_ts)
    assert sum_1d.workouts_count == 2
    assert sum_1d.days == 1

    # days=7: all 3 workouts are within window
    sum_7d = await get_training_summary(days=7, now_ts=ref_ts)
    assert sum_7d.workouts_count == 3
    assert sum_7d.days == 7


@pytest.mark.asyncio
async def test_days_filtering_recent_activities_summary():
    """Bug 3: get_recent_activities_summary actually filters by days window."""
    ref_ts = 1789320000000.0

    rec_1d = await get_recent_activities_summary(days=1, now_ts=ref_ts)
    assert rec_1d.total_sessions == 2
    assert rec_1d.days == 1

    rec_7d = await get_recent_activities_summary(days=7, now_ts=ref_ts)
    assert rec_7d.total_sessions == 3
    assert rec_7d.days == 7


@pytest.mark.asyncio
async def test_pagination_wider_window(monkeypatch):
    """Bug 5: _fetch_workouts_for_days paginates through multiple pages until pre-dating window."""
    ref_ts = 1789320000000.0
    cutoff_ms = ref_ts - (30 * 86400.0 * 1000.0)

    # Generate 60 workouts in window and 1 older workout
    page1 = [
        {"workoutKey": f"p1_{i}", "startTime": ref_ts - (i * 10000), "activityId": 1}
        for i in range(50)
    ]
    page2 = [
        {
            "workoutKey": f"p2_{i}",
            "startTime": ref_ts - ((50 + i) * 10000),
            "activityId": 1,
        }
        for i in range(10)
    ] + [
        {"workoutKey": "old_workout", "startTime": cutoff_ms - 100000, "activityId": 1}
    ]

    async def mock_paginated_workouts(limit=50, offset=0, **kwargs):
        if offset == 0:
            return page1
        elif offset == 50:
            return page2
        return []

    monkeypatch.setattr(tools.client, "get_workouts", mock_paginated_workouts)
    fetched = await tools._fetch_workouts_for_days(days=30, now_ts=ref_ts)
    assert len(fetched) == 60
    assert all(w["workoutKey"] != "old_workout" for w in fetched)


@pytest.mark.asyncio
async def test_fetch_workouts_safety_cap(monkeypatch, caplog):
    """Verify safety cap breaks loop and logs warning when offset hits max_workouts."""
    ref_ts = 1789320000000.0

    async def mock_endless_workouts(limit=50, offset=0, **kwargs):
        # Always return full pages of recent workouts
        return [
            {
                "workoutKey": f"w_{offset}_{i}",
                "startTime": ref_ts - 1000,
                "activityId": 1,
            }
            for i in range(limit)
        ]

    monkeypatch.setattr(tools.client, "get_workouts", mock_endless_workouts)

    import logging

    with caplog.at_level(logging.WARNING):
        fetched = await tools._fetch_workouts_for_days(
            days=30, now_ts=ref_ts, max_workouts=100
        )

    # 2 pages of 50 = 100 workouts before cap hit
    assert len(fetched) == 100
    assert any("safety limit" in record.message for record in caplog.records)
