from sport_tracker_mcp.models import (
    ActivityCount,
    RecentActivitiesSummary,
    SocialFeedItem,
    SportStats,
    TrainingLoadAndRecovery,
    TrainingSummary,
    UserStats,
    VO2MaxHistory,
    VO2MaxRecord,
    WorkoutDetail,
    WorkoutSummary,
)
from tests.fixtures import (
    MOCK_USER_FEED_PAYLOAD,
    MOCK_USER_STATS_PAYLOAD,
    MOCK_WORKOUT_DETAILS_PAYLOAD,
    MOCK_WORKOUTS_PAYLOAD,
)

# ============================================================================
# 1. WorkoutSummary & WorkoutDetail
# ============================================================================


def test_workout_summary_and_detail():
    # Test WorkoutDetail from MOCK_WORKOUTS_PAYLOAD[0] (Walking with rich extensions)
    detail = WorkoutDetail.from_api(MOCK_WORKOUTS_PAYLOAD[0])

    assert isinstance(detail, WorkoutSummary)
    assert detail.workout_key == "6aa6e2cc73ed6b7db03df35c"
    assert detail.sport == "walking"
    assert detail.duration_formatted == "01:05:07"
    assert detail.distance_formatted == "1.19 km"
    assert detail.avg_speed_formatted == "1.1 km/h"
    assert detail.avg_pace_formatted == "55:33"
    assert detail.distance_km == 1.19
    assert detail.duration_seconds == 3907.3
    assert detail.calories_kcal == 295
    assert detail.avg_hr == 91
    assert detail.max_hr == 121
    assert detail.step_count == 1270

    # Detail extensions
    assert detail.ascent_meters == 20.2
    assert detail.descent_meters == 17.5
    assert detail.recovery_time_hours == 0.6  # 2100s / 3600
    assert detail.cumulative_recovery_hours == 6.8  # 24600s / 3600
    assert detail.training_stress_score == 38.6
    assert detail.peak_training_effect == 1.3
    assert detail.peak_epoc == 3.5
    assert detail.gear == "Suunto Race"


def test_workout_detail_hr_zones():
    # Test IntensityExtension HR zones on MOCK_WORKOUTS_PAYLOAD[1] (Gym)
    detail = WorkoutDetail.from_api(MOCK_WORKOUTS_PAYLOAD[1])
    assert detail.sport == "gym"
    assert detail.heart_rate_zones is not None
    assert detail.heart_rate_zones["zone1"] == "00:34:44"
    assert detail.heart_rate_zones["zone2"] == "00:11:26"
    assert detail.heart_rate_zones["zone3"] == "00:07:49"
    assert detail.heart_rate_zones["zone4"] == "00:06:47"
    assert detail.heart_rate_zones["zone5"] == "00:01:42"


# ============================================================================
# 2. SocialFeedItem
# ============================================================================


def test_social_feed_item_ambassador():
    ambassador_raw = MOCK_USER_FEED_PAYLOAD[0]
    item = SocialFeedItem.from_api(ambassador_raw)
    assert item.feed_type == "AMBASSADOR"
    assert item.workout_key is None
    assert item.sport is None
    assert item.distance_formatted is None


def test_social_feed_item_workout():
    workout_raw = MOCK_USER_FEED_PAYLOAD[1]
    item = SocialFeedItem.from_api(workout_raw)
    assert item.feed_type == "WORKOUT"
    assert item.username == "mock_athlete"
    assert item.athlete_name == "Mock Athlete"
    assert item.workout_key == "6aa6e2cc73ed6b7db03df35c"
    assert item.sport == "walking"
    assert item.duration_formatted == "01:05:07"
    assert item.distance_formatted == "1.19 km"
    assert item.avg_speed_formatted == "1.1 km/h"


# ============================================================================
# 3. UserStats & SportStats
# ============================================================================


def test_user_stats():
    stats = UserStats.from_api(MOCK_USER_STATS_PAYLOAD)
    assert stats.total_distance_km == 9855.35
    assert stats.total_distance_formatted == "9,855.35 km"
    assert stats.total_duration_hours == 3026.2
    assert stats.total_workouts == 2651
    assert stats.total_calories_kcal == 1460192
    assert stats.total_days == 1858
    assert len(stats.sports) == 4

    sports_by_name = {s.sport: s for s in stats.sports}
    assert "walking" in sports_by_name
    assert sports_by_name["walking"].workouts_count == 1015
    assert sports_by_name["walking"].distance_km == 3408.02
    assert sports_by_name["walking"].distance_formatted == "3,408.02 km"
    assert sports_by_name["walking"].calories_kcal == 470174

    assert "gym" in sports_by_name
    assert sports_by_name["gym"].workouts_count == 927


# ============================================================================
# 4. VO2MaxHistory & VO2MaxRecord
# ============================================================================


def test_vo2_max_history():
    history = VO2MaxHistory.from_workouts(MOCK_WORKOUTS_PAYLOAD)

    # Only MOCK_WORKOUTS_PAYLOAD[0] has FitnessExtension with vo2Max
    assert len(history.records) == 1
    rec = history.records[0]
    assert rec.sport == "walking"
    assert rec.workout_key == "6aa6e2cc73ed6b7db03df35c"
    assert rec.vo2_max == 39.0
    assert rec.estimated_vo2_max == 38.9
    assert rec.fitness_age == 45
    assert rec.max_hr == 186

    assert history.latest_vo2_max == 39.0
    assert history.average_vo2_max == 39.0
    assert history.latest_fitness_age == 45


def test_vo2_max_history_empty():
    history = VO2MaxHistory.from_workouts([])
    assert history.records == []
    assert history.latest_vo2_max is None
    assert history.average_vo2_max is None
    assert history.latest_fitness_age is None


# ============================================================================
# 5. TrainingSummary & SportStats
# ============================================================================


def test_training_summary():
    summary = TrainingSummary.from_workouts(MOCK_WORKOUTS_PAYLOAD, days=7)
    assert summary.days == 7
    assert summary.workouts_count == 3
    # 1189m + 0m + 3194m = 4383m = 4.38 km
    assert summary.total_distance_km == 4.38
    assert summary.total_distance_formatted == "4.38 km"
    # 3907.322 + 3750.841 + 1344.967 = 9003.13s = 02:30:03
    assert summary.total_duration_formatted == "02:30:03"
    # 295 + 637 + 148 = 1080 kcal
    assert summary.total_calories_kcal == 1080
    assert len(summary.sports) == 3

    sports_map = {s.sport: s for s in summary.sports}
    assert "walking" in sports_map
    assert "gym" in sports_map
    assert "cycling" in sports_map
    assert sports_map["cycling"].distance_km == 3.19
    assert sports_map["cycling"].calories_kcal == 148


# ============================================================================
# 6. TrainingLoadAndRecovery
# ============================================================================


def test_training_load_and_recovery():
    recovery = TrainingLoadAndRecovery.from_workout(MOCK_WORKOUTS_PAYLOAD[0])
    assert recovery.latest_workout_key == "6aa6e2cc73ed6b7db03df35c"
    assert recovery.latest_sport == "walking"
    assert recovery.cumulative_recovery_hours == 6.8
    assert recovery.latest_workout_recovery_hours == 0.6
    assert recovery.training_stress_score == 38.6
    assert recovery.peak_training_effect == 1.3
    assert recovery.peak_epoc == 3.5
    assert recovery.impact_tag == "IMPACT_LONG_AEROBIC_BASE"
    # 6.8h < 12h -> Ready for Training
    assert recovery.recovery_status == "Ready for Training"


def test_training_load_and_recovery_empty():
    recovery = TrainingLoadAndRecovery.from_workout(None)
    assert recovery.cumulative_recovery_hours == 0.0
    assert recovery.recovery_status == "Fully Recovered"


# ============================================================================
# 7. RecentActivitiesSummary & ActivityCount
# ============================================================================


def test_recent_activities_summary():
    recent = RecentActivitiesSummary.from_workouts(MOCK_WORKOUTS_PAYLOAD, days=14)
    assert recent.days == 14
    assert recent.total_sessions == 3
    assert len(recent.activities) == 3

    sports_counted = {a.sport: a.count for a in recent.activities}
    assert sports_counted["walking"] == 1
    assert sports_counted["gym"] == 1
    assert sports_counted["cycling"] == 1


def test_workout_summary_from_api_missing_keys():
    # Incomplete inputs return None without raising KeyError
    assert WorkoutSummary.from_api({}) is None
    assert WorkoutSummary.from_api({"startTime": 1789317924710}) is None
    assert WorkoutSummary.from_api({"workoutKey": "k1"}) is None
    assert WorkoutDetail.from_api({}) is None
    assert WorkoutDetail.from_api({"workoutKey": "k1"}) is None


def test_workout_summary_non_numeric_fields():
    # Non-numeric strings in numeric fields should not raise ValueError
    raw = {
        "workoutKey": "k_safe",
        "startTime": 1789317924710,
        "totalDistance": "n/a",
        "totalTime": "invalid",
        "avgSpeed": None,
        "energyConsumption": "corrupted",
    }
    summary = WorkoutSummary.from_api(raw)
    assert summary is not None
    assert summary.distance_km == 0.0
    assert summary.distance_formatted == "0.00 km"
    assert summary.duration_seconds == 0.0
    assert summary.calories_kcal is None


def test_social_feed_item_explicit_null_fields():
    # Feeds with explicit null numeric fields should not raise TypeError
    raw = {
        "feedType": "WORKOUT",
        "username": "athlete1",
        "workoutKey": "key123",
        "activityId": 1,
        "startTime": 1789317924710,
        "totalDistance": None,
        "totalTime": None,
        "avgSpeed": None,
        "reactionCount": None,
        "commentCount": None,
        "description": None,
    }
    item = SocialFeedItem.from_api(raw)
    assert item.feed_type == "WORKOUT"
    assert item.distance_formatted is None
    assert item.duration_formatted is None
    assert item.avg_speed_formatted is None
    assert item.likes_count == 0
    assert item.comments_count == 0


def test_user_stats_explicit_null_fields():
    # Brand new account or stats with explicit nulls should not raise TypeError
    raw = {
        "totalDistanceSum": None,
        "totalTimeSum": None,
        "totalNumberOfWorkoutsSum": None,
        "totalEnergyConsumptionSum": None,
        "totalDays": None,
        "allStats": [
            {
                "_id": 1,
                "totalDistance": None,
                "totalTime": None,
                "numberOfWorkouts": None,
                "energyConsumption": None,
            }
        ],
    }
    stats = UserStats.from_api(raw)
    assert stats.total_distance_km == 0.0
    assert stats.total_duration_hours == 0.0
    assert stats.total_workouts == 0
    assert stats.total_calories_kcal == 0
    assert stats.total_days == 0
    assert len(stats.sports) == 1
    assert stats.sports[0].workouts_count == 0
    assert stats.sports[0].distance_km == 0.0
    assert stats.sports[0].duration_hours == 0.0
    assert stats.sports[0].calories_kcal == 0


def test_workout_detail_explicit_null_metrics():
    # Workout detail with explicit nulls in ascent/descent and intensity zones
    raw = {
        "workoutKey": "wk123",
        "startTime": 1789317924710,
        "activityId": 1,
        "totalDistance": 1000.0,
        "totalTime": 600.0,
        "totalAscent": None,
        "totalDescent": None,
        "extensions": [
            {
                "type": "IntensityExtension",
                "zones": {
                    "heartRate": {
                        "zone1": {"totalTime": None},
                        "zone2": {"totalTime": 120.0},
                    }
                },
            }
        ],
    }
    detail = WorkoutDetail.from_api(raw)
    assert detail is not None
    assert detail.ascent_meters == 0.0
    assert detail.descent_meters == 0.0
    assert detail.heart_rate_zones is not None
    assert detail.heart_rate_zones["zone1"] == "00:00:00"
    assert detail.heart_rate_zones["zone2"] == "00:02:00"
