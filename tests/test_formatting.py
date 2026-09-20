import pytest

from sport_tracker_mcp.formatting import (
    format_distance,
    format_duration,
    format_pace,
    format_speed,
)
from tests.fixtures import (
    MOCK_WORKOUT_DETAILS_PAYLOAD,
    MOCK_WORKOUTS_PAYLOAD,
    make_mock_workout,
)

# ============================================================================
# 1. Distance Formatting Tests
# ============================================================================


def test_format_distance_from_mock_workouts():
    # Workout 0: 1189.0 meters (walking)
    walk_wo = MOCK_WORKOUTS_PAYLOAD[0]
    km, formatted_km = format_distance(walk_wo["totalDistance"], imperial=False)
    assert km == 1.19
    assert formatted_km == "1.19 km"

    mi, formatted_mi = format_distance(walk_wo["totalDistance"], imperial=True)
    assert mi == 0.74
    assert formatted_mi == "0.74 mi"

    # Workout 2: 3194.0 meters (cycling)
    cycling_wo = MOCK_WORKOUTS_PAYLOAD[2]
    km, formatted_km = format_distance(cycling_wo["totalDistance"])
    assert km == 3.19
    assert formatted_km == "3.19 km"


def test_format_distance_zero_and_empty():
    # Workout 1: 0.0 meters (gym)
    gym_wo = MOCK_WORKOUTS_PAYLOAD[1]
    val, formatted = format_distance(gym_wo["totalDistance"])
    assert val == 0.0
    assert formatted == "0.00 km"

    val_mi, formatted_mi = format_distance(0.0, imperial=True)
    assert val_mi == 0.0
    assert formatted_mi == "0.00 mi"


def test_format_distance_thresholds_from_routes_and_factory():
    # Long distance: 10502.4 meters (10.5 km -> <= 100 km threshold: 2 decimals)
    route_dist = 10502.4
    val, formatted = format_distance(route_dist)
    assert val == 10.5
    assert formatted == "10.50 km"

    # Mock Factory: 5000.0 meters (5 km)
    mock_wo = make_mock_workout()
    val, formatted = format_distance(mock_wo["totalDistance"])
    assert val == 5.0
    assert formatted == "5.00 km"

    # Medium distance: 250.6 km
    val, formatted = format_distance(250_600.0)
    assert val == 250.6
    assert formatted == "250.60 km"

    # Ultra-long distance: 1,250.4 km
    val, formatted = format_distance(1_250_400.0)
    assert val == 1250.4
    assert formatted == "1,250.40 km"


# ============================================================================
# 2. Speed Formatting Tests
# ============================================================================


def test_format_speed_from_mock_workouts():
    # Workout 0: avgSpeed = 0.3 m/s
    walk_wo = MOCK_WORKOUTS_PAYLOAD[0]
    formatted_kmh = format_speed(walk_wo["avgSpeed"], imperial=False)
    assert formatted_kmh == "1.1 km/h"

    formatted_mph = format_speed(walk_wo["avgSpeed"], imperial=True)
    assert formatted_mph == "0.7 mph"

    # Workout 1: avgSpeed = 0.0 m/s
    gym_wo = MOCK_WORKOUTS_PAYLOAD[1]
    formatted_zero = format_speed(gym_wo["avgSpeed"])
    assert formatted_zero == "0.0 km/h"

    # Workout 2: avgSpeed = 2.37 m/s (2.37 * 3.6 = 8.532 -> 8.5 km/h)
    cycling_wo = MOCK_WORKOUTS_PAYLOAD[2]
    formatted_kmh = format_speed(cycling_wo["avgSpeed"])
    assert formatted_kmh == "8.5 km/h"


def test_format_speed_from_routes_and_factory():
    # Speed: 2.5 m/s (2.5 * 3.6 = 9.0 km/h)
    route_speed = 2.5
    formatted_kmh = format_speed(route_speed, imperial=False)
    assert formatted_kmh == "9.0 km/h"

    formatted_mph = format_speed(route_speed, imperial=True)
    assert formatted_mph == "5.6 mph"

    # Factory helper: avgSpeed = 2.78 m/s (2.78 * 3.6 = 10.008 -> 10.0 km/h)
    mock_wo = make_mock_workout()
    formatted_kmh = format_speed(mock_wo["avgSpeed"])
    assert formatted_kmh == "10.0 km/h"


# ============================================================================
# 3. Pace Formatting Tests
# ============================================================================


def test_format_pace_from_mock_workouts():
    # Workout 0: avgSpeed = 0.3 m/s -> pace ~ 55:33 min/km
    walk_wo = MOCK_WORKOUTS_PAYLOAD[0]
    pace_km = format_pace(walk_wo["avgSpeed"], imperial=False)
    assert pace_km == "55:33"

    pace_mi = format_pace(walk_wo["avgSpeed"], imperial=True)
    assert pace_mi == "89:24"

    # Workout 1: avgSpeed = 0.0 m/s -> "00:00"
    gym_wo = MOCK_WORKOUTS_PAYLOAD[1]
    assert format_pace(gym_wo["avgSpeed"]) == "00:00"
    assert format_pace(-1.0) == "00:00"


def test_format_pace_from_factory():
    # Factory: avgSpeed = 2.78 m/s (10.008 km/h -> pace ~ 5:59 min/km)
    mock_wo = make_mock_workout()
    pace_km = format_pace(mock_wo["avgSpeed"], imperial=False)
    assert pace_km == "5:59"

    # Speed: 2.5 m/s (9.0 km/h -> 60/9 = 6.666 -> 6:40 min/km)
    route_pace = format_pace(2.5)
    assert route_pace == "6:40"


def test_format_duration_edge_cases():
    assert format_duration(0) == "00:00:00"
    assert format_duration(45) == "00:00:45"
    assert format_duration(3665) == "01:01:05"
    assert format_duration(90000) == "25:00:00"
