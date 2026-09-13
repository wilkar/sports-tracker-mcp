"""Anonymized test fixtures for Sports Tracker API responses."""

from typing import Any

import httpx


def sports_tracker_mock_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/workouts") and request.method == "GET":
        return httpx.Response(200, json={"payload": MOCK_WORKOUTS_PAYLOAD})
    elif "/workouts/" in path and path.endswith("/combined"):
        return httpx.Response(200, json={"payload": MOCK_WORKOUT_DETAILS_PAYLOAD})
    elif path.endswith("/user/feed/combined"):
        return httpx.Response(200, json={"payload": MOCK_USER_FEED_PAYLOAD})
    elif "/workouts/" in path and path.endswith("/stats"):
        return httpx.Response(200, json={"payload": MOCK_USER_STATS_PAYLOAD})
    elif path.endswith("/user/follow"):
        return httpx.Response(200, json={"payload": MOCK_USER_FOLLOWING_PAYLOAD})
    elif path.endswith("/user"):
        return httpx.Response(200, json={"payload": MOCK_USER_SETTINGS_PAYLOAD})
    elif path.endswith("/routes"):
        return httpx.Response(200, json={"payload": MOCK_ROUTES_PAYLOAD})
    elif "/routes/" in path:
        return httpx.Response(200, json={"payload": MOCK_ROUTES_PAYLOAD[0]})
    elif "/workout/exportGpx/" in path:
        return httpx.Response(
            200,
            text=MOCK_GPX_XML,
            headers={"content-disposition": 'attachment; filename="workout.gpx"'},
        )
    return httpx.Response(404, json={"error": "Not Found"})


# ============================================================================
# 1. Workouts List (GET /workouts)
# ============================================================================
MOCK_WORKOUTS_PAYLOAD: list[dict[str, Any]] = [
    {
        # Walking workout
        "username": "mock_athlete",
        "sharingFlags": 17,
        "activityId": 0,
        "key": "mock_walk_key_001",
        "workoutKey": "6aa6e2cc73ed6b7db03df35c",
        "startTime": 1789317924710,
        "stopTime": 1789321830990,
        "totalTime": 3907.322,
        "totalDistance": 1189.0,
        "avgSpeed": 0.3,
        "avgPace": 54.77,
        "maxSpeed": 2.84,
        "energyConsumption": 295,
        "stepCount": 1270,
        "recoveryTime": 2100,
        "cumulativeRecoveryTime": 24600,
        "tss": {"calculationMethod": "HR", "trainingStressScore": 38.59928},
        "suuntoTags": ["IMPACT_LONG_AEROBIC_BASE"],
        "totalAscent": 20.2,
        "totalDescent": 17.5,
        "startPosition": {"x": 0.0, "y": 0.0},
        "stopPosition": {"x": 0.0, "y": 0.0},
        "centerPosition": {"x": 0.0, "y": 0.0},
        "polyline": "mock_polyline_walk",
        "hrdata": {
            "workoutMaxHR": 121,
            "workoutAvgHR": 91,
            "userMaxHR": 186,
            "hrmax": 121,
            "avg": 91,
            "max": 186,
        },
        "cadence": {"max": 108, "avg": 51},
        "extensions": [
            {
                "type": "FitnessExtension",
                "maxHeartRate": 186,
                "vo2Max": 39,
                "estimatedVo2Max": 38.9,
                "fitnessAge": 45,
            },
            {
                "type": "SummaryExtension",
                "avgSpeed": 0.304,
                "pte": 1.3,
                "peakEpoc": 3.5,
                "gear": {
                    "manufacturer": "Suunto",
                    "name": "Tianjin",
                    "displayName": "Suunto Race",
                    "serialNumber": "SN000000000",
                    "softwareVersion": "2.53.42",
                    "hardwareVersion": "Phoenix_RevB1",
                    "productType": "SPORT_WATCH",
                },
            },
        ],
    },
    {
        # Gym / Strength workout (zero distance/speed)
        "username": "mock_athlete",
        "sharingFlags": 17,
        "activityId": 23,  # gym
        "key": "mock_gym_key_002",
        "workoutKey": "6aa68b384eeeb6216b2d466b",
        "startTime": 1789295335480,
        "stopTime": 1789299085260,
        "totalTime": 3750.841,
        "totalDistance": 0.0,
        "avgSpeed": 0.0,
        "avgPace": 0.0,
        "maxSpeed": 0.0,
        "energyConsumption": 637,
        "stepCount": 0,
        "totalAscent": 0.0,
        "totalDescent": 0.0,
        "startPosition": {"x": 0.0, "y": 0.0},
        "stopPosition": {"x": 0.0, "y": 0.0},
        "centerPosition": {"x": 0.0, "y": 0.0},
        "polyline": "",
        "hrdata": {
            "workoutMaxHR": 169,
            "workoutAvgHR": 132,
            "userMaxHR": 186,
            "hrmax": 169,
            "avg": 132,
            "max": 186,
        },
        "cadence": {"max": 0, "avg": 0},
        "extensions": [
            {
                "type": "IntensityExtension",
                "zones": {
                    "heartRate": {
                        "zone1": {"totalTime": 2084.811, "lowerLimit": 0.0},
                        "zone2": {"totalTime": 686.061, "lowerLimit": 134.0},
                        "zone3": {"totalTime": 469.129, "lowerLimit": 143.0},
                        "zone4": {"totalTime": 407.937, "lowerLimit": 153.0},
                        "zone5": {"totalTime": 102.948, "lowerLimit": 162.0},
                    }
                },
            }
        ],
    },
    {
        # Cycling workout
        "username": "mock_athlete",
        "sharingFlags": 17,
        "activityId": 2,  # cycling
        "key": "mock_cycling_key_003",
        "workoutKey": "6aa51ebbb8ec551cf5e84e70",
        "startTime": 1789204574340,
        "stopTime": 1789205919300,
        "totalTime": 1344.967,
        "totalDistance": 3194.0,
        "avgSpeed": 2.37,
        "avgPace": 7.02,
        "maxSpeed": 9.0,
        "energyConsumption": 148,
        "stepCount": 0,
        "totalAscent": 33.5,
        "totalDescent": 29.9,
        "startPosition": {"x": 0.0, "y": 0.0},
        "stopPosition": {"x": 0.0, "y": 0.0},
        "centerPosition": {"x": 0.0, "y": 0.0},
        "polyline": "mock_polyline_cycling",
        "hrdata": {
            "workoutMaxHR": 154,
            "workoutAvgHR": 103,
            "userMaxHR": 186,
            "hrmax": 154,
            "avg": 103,
            "max": 186,
        },
        "cadence": {"max": 0, "avg": 0},
        "description": "Afternoon Ride",
        "extensions": [
            {
                "type": "SummaryExtension",
                "avgSpeed": 2.375,
                "ascent": 33.5,
                "descent": 29.9,
            }
        ],
    },
]


# ============================================================================
# 2. Workout Details Combined (GET /workouts/{key}/combined)
# ============================================================================
MOCK_WORKOUT_DETAILS_PAYLOAD: dict[str, Any] = {
    "feedType": "WORKOUT",
    "username": "mock_athlete",
    "fullname": "Mock Athlete",
    "activityId": 2,
    "key": "mock_cycling_key_003",
    "workoutKey": "6aa51ebbb8ec551cf5e84e70",
    "workoutName": "Commute",
    "description": "Afternoon Ride",
    "startTime": 1789204574340,
    "stopTime": 1789205919300,
    "totalTime": 1344.967,
    "totalDistance": 3194.0,
    "avgSpeed": 2.37,
    "avgPace": 7.02,
    "maxSpeed": 9.0,
    "energyConsumption": 148,
    "stepCount": 0,
    "totalAscent": 33.5,
    "totalDescent": 29.9,
    "startPosition": {"x": 0.0, "y": 0.0},
    "stopPosition": {"x": 0.0, "y": 0.0},
    "centerPosition": {"x": 0.0, "y": 0.0},
    "polyline": "mock_polyline_cycling",
    "hrdata": {
        "workoutMaxHR": 154,
        "workoutAvgHR": 103,
        "userMaxHR": 186,
        "hrmax": 154,
        "avg": 103,
        "max": 186,
    },
    "cadence": {"max": 0, "avg": 0},
    "extensions": [
        {
            "type": "SummaryExtension",
            "avgSpeed": 2.375,
            "ascent": 33.5,
            "descent": 29.9,
            "gear": {
                "manufacturer": "Suunto",
                "displayName": "Suunto Race",
                "serialNumber": "SN000000000",
                "productType": "SPORT_WATCH",
            },
        },
        {
            "type": "AltitudeStreamExtension",
            "points": [
                {"value": 204.6, "timestamp": 1789204574340},
                {"value": 206.0, "timestamp": 1789204575340},
                {"value": 208.5, "timestamp": 1789204576340},
            ],
        },
    ],
}


# ============================================================================
# 3. User Feed (GET /user/feed/combined)
# ============================================================================
MOCK_USER_FEED_PAYLOAD: list[dict[str, Any]] = [
    {"feedType": "AMBASSADOR"},
    {
        "feedType": "WORKOUT",
        "username": "mock_athlete",
        "fullname": "Mock Athlete",
        "activityId": 0,
        "workoutKey": "6aa6e2cc73ed6b7db03df35c",
        "startTime": 1789317924710,
        "totalTime": 3907.322,
        "totalDistance": 1189.0,
        "energyConsumption": 295,
        "avgSpeed": 0.3,
        "hrdata": {"avg": 91, "hrmax": 121},
    },
]


# ============================================================================
# 4. User Stats (GET /workouts/{username}/stats)
# ============================================================================
MOCK_USER_STATS_PAYLOAD: dict[str, Any] = {
    "totalDistanceSum": 9855354.22,
    "totalTimeSum": 10894226.598,
    "totalEnergyConsumptionSum": 1460192.0,
    "totalNumberOfWorkoutsSum": 2651,
    "totalDays": 1858,
    "allStats": [
        {
            "_id": 0,  # walking
            "totalDistance": 3408019.41,
            "totalTime": 5172877.43,
            "energyConsumption": 470174,
            "numberOfWorkouts": 1015,
        },
        {
            "_id": 23,  # gym
            "totalDistance": 418.19,
            "totalTime": 3683374.37,
            "energyConsumption": 522277,
            "numberOfWorkouts": 927,
        },
        {
            "_id": 1,  # running
            "totalDistance": 1838450.63,
            "totalTime": 689502.51,
            "energyConsumption": 229971,
            "numberOfWorkouts": 276,
        },
        {
            "_id": 2,  # cycling
            "totalDistance": 3885015.99,
            "totalTime": 647130.47,
            "energyConsumption": 127224,
            "numberOfWorkouts": 190,
        },
    ],
}


# ============================================================================
# 5. User Settings (GET /user)
# ============================================================================
MOCK_USER_SETTINGS_PAYLOAD: dict[str, Any] = {
    "username": "mock_athlete",
    "realName": "Mock Athlete",
    "country": "PL",
    "gender": "MALE",
    "description": "Fitness enthusiast",
    "uuid": "00000000-0000-0000-0000-000000000001",
    "key": "5e10eb650000000000000001",
    "showLocale": True,
    "automaticallyApproveFollowers": False,
    "followModel": True,
}


# ============================================================================
# 6. User Following (GET /user/follow)
# ============================================================================
MOCK_USER_FOLLOWING_PAYLOAD: dict[str, Any] = {
    "followers": [
        {
            "username": "mock_follower_1",
            "status": "FOLLOWING",
            "realName": "Follower One",
            "profileDescription": "",
            "profileImageUrl": None,
            "coverImageUrl": None,
        }
    ],
    "followings": [
        {
            "username": "mock_follower_1",
            "status": "FOLLOWING",
            "realName": "Follower One",
            "profileDescription": "",
            "profileImageUrl": None,
            "coverImageUrl": None,
        }
    ],
    "blocked": [],
    "blockedBy": [],
}


# ============================================================================
# 7. Routes (GET /routes and GET /routes/{id})
# ============================================================================
MOCK_ROUTES_PAYLOAD: list[dict[str, Any]] = [
    {
        "id": "5ebef41b4a01021a667a04c4",
        "username": "mock_athlete",
        "description": "City Loop",
        "activities": [1],
        "totalDistance": 10502.4,
        "averageSpeed": 2.5,
        "visibility": "PRIVATE",
        "startPoint": {"x": 0.0, "y": 0.0},
        "endPoint": {"x": 0.0, "y": 0.0},
        "segments": [
            {
                "position": 0,
                "start": {"x": 0.0, "y": 0.0},
                "end": {"x": 0.01, "y": 0.01},
                "polyline": "mock_route_segment_polyline",
                "routePoints": [
                    {"x": 0.0, "y": 0.0, "z": 240.0},
                    {"x": 0.005, "y": 0.005, "z": 242.0},
                    {"x": 0.01, "y": 0.01, "z": 245.0},
                ],
            }
        ],
    }
]


# ============================================================================
# 8. GPX Export (GET /workout/exportGpx/{key})
# ============================================================================
MOCK_GPX_XML: str = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" 
     xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" 
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
     creator="Sports Tracker" version="1.1" 
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <metadata>
    <name>Morning Activity</name>
    <author>
      <name>Mock Athlete</name>
    </author>
  </metadata>
  <trk>
    <name>Commute</name>
    <trkseg>
      <trkpt lat="50.0000" lon="20.0000">
        <time>2026-09-13T10:28:55Z</time>
        <extensions>
          <gpxtpx:TrackPointExtension>
            <gpxtpx:hr>116</gpxtpx:hr>
          </gpxtpx:TrackPointExtension>
        </extensions>
      </trkpt>
      <trkpt lat="50.0001" lon="20.0002">
        <time>2026-09-13T10:28:56Z</time>
        <extensions>
          <gpxtpx:TrackPointExtension>
            <gpxtpx:hr>122</gpxtpx:hr>
          </gpxtpx:TrackPointExtension>
        </extensions>
      </trkpt>
      <trkpt lat="50.0003" lon="20.0005">
        <time>2026-09-13T10:28:57Z</time>
        <extensions>
          <gpxtpx:TrackPointExtension>
            <gpxtpx:hr>130</gpxtpx:hr>
          </gpxtpx:TrackPointExtension>
        </extensions>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


# ============================================================================
# 9. Factory Helper for Custom Workout Overrides
# ============================================================================
def make_mock_workout(**overrides: Any) -> dict[str, Any]:
    """Helper to return an anonymized workout payload with custom overrides."""
    base = {
        "username": "mock_athlete",
        "workoutKey": "mock_custom_key_999",
        "activityId": 1,  # running
        "startTime": 1789204574340,
        "stopTime": 1789206374340,
        "totalTime": 1800.0,
        "totalDistance": 5000.0,
        "avgSpeed": 2.78,
        "avgPace": 6.0,
        "energyConsumption": 380,
        "stepCount": 2600,
        "hrdata": {"avg": 142, "hrmax": 168},
        "description": "Afternoon Run",
    }
    return {**base, **overrides}
