import asyncio

import httpx
import pytest

from sport_tracker_mcp.client.client import (
    SportsTrackerAPIError,
    SportsTrackerAuthenticationError,
    SportsTrackerClient,
    SportsTrackerError,
    SportsTrackerNotFoundError,
)
from tests.fixtures import (
    MOCK_GPX_XML,
    MOCK_ROUTES_PAYLOAD,
    MOCK_USER_FEED_PAYLOAD,
    MOCK_USER_FOLLOWING_PAYLOAD,
    MOCK_USER_SETTINGS_PAYLOAD,
    MOCK_USER_STATS_PAYLOAD,
    MOCK_WORKOUT_DETAILS_PAYLOAD,
    MOCK_WORKOUTS_PAYLOAD,
    make_mock_workout,
    sports_tracker_mock_handler,
)


@pytest.fixture
def client() -> SportsTrackerClient:
    transport = httpx.MockTransport(sports_tracker_mock_handler)
    return SportsTrackerClient(session_key="mock-session-key", transport=transport)


# ============================================================================
# 1. Successful API Calls Using Fixtures
# ============================================================================


@pytest.mark.asyncio
async def test_get_workouts(client: SportsTrackerClient):
    workouts = await client.get_workouts(limit=50, offset=0)
    assert len(workouts) == len(MOCK_WORKOUTS_PAYLOAD)
    assert workouts[0]["workoutKey"] == MOCK_WORKOUTS_PAYLOAD[0]["workoutKey"]
    assert workouts[0]["username"] == "mock_athlete"


@pytest.mark.asyncio
async def test_get_workout_details(client: SportsTrackerClient):
    workout_key = "6aa6e2cc73ed6b7db03df35c"
    details = await client.get_workout_details(workout_key)
    assert details == MOCK_WORKOUT_DETAILS_PAYLOAD
    assert details["workoutKey"] == MOCK_WORKOUT_DETAILS_PAYLOAD["workoutKey"]
    assert "extensions" in details


@pytest.mark.asyncio
async def test_get_social_feed(client: SportsTrackerClient):
    feed = await client.get_social_feed(limit=10, offset=0)
    assert feed == MOCK_USER_FEED_PAYLOAD
    assert isinstance(feed, list)
    assert feed[0]["feedType"] == "AMBASSADOR"
    assert feed[1]["feedType"] == "WORKOUT"
    assert feed[1]["workoutKey"] == "6aa6e2cc73ed6b7db03df35c"


@pytest.mark.asyncio
async def test_get_user_stats(client: SportsTrackerClient):
    stats = await client.get_user_stats("mock_athlete")
    assert stats == MOCK_USER_STATS_PAYLOAD
    assert "totalDistanceSum" in stats
    assert (
        stats["totalNumberOfWorkoutsSum"]
        == MOCK_USER_STATS_PAYLOAD["totalNumberOfWorkoutsSum"]
    )
    assert len(stats["allStats"]) == 4


@pytest.mark.asyncio
async def test_get_user_settings(client: SportsTrackerClient):
    settings = await client.get_user_settings()
    assert settings == MOCK_USER_SETTINGS_PAYLOAD
    assert settings["username"] == "mock_athlete"
    assert settings["realName"] == "Mock Athlete"
    assert settings["country"] == "PL"


@pytest.mark.asyncio
async def test_get_user_following(client: SportsTrackerClient):
    following = await client.get_user_following()
    assert following == MOCK_USER_FOLLOWING_PAYLOAD
    assert "followers" in following
    assert "followings" in following
    assert len(following["followers"]) == 1


@pytest.mark.asyncio
async def test_get_routes(client: SportsTrackerClient):
    routes = await client.get_routes()
    assert routes == MOCK_ROUTES_PAYLOAD
    assert len(routes) == len(MOCK_ROUTES_PAYLOAD)
    assert routes[0]["id"] == MOCK_ROUTES_PAYLOAD[0]["id"]


@pytest.mark.asyncio
async def test_get_single_route(client: SportsTrackerClient):
    route_id = MOCK_ROUTES_PAYLOAD[0]["id"]
    route = await client.get_route(route_id)
    assert route == MOCK_ROUTES_PAYLOAD[0]
    assert route["description"] == "City Loop"


@pytest.mark.asyncio
async def test_export_activity_with_disposition(client: SportsTrackerClient):
    workout_key = "6aa6e2cc73ed6b7db03df35c"
    text, filename = await client.export_activity(workout_key)
    assert text == MOCK_GPX_XML
    assert filename == "workout.gpx"


@pytest.mark.asyncio
async def test_export_activity_fallback_filename():
    def custom_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=MOCK_GPX_XML)

    client = SportsTrackerClient(
        session_key="mock-session-key",
        transport=httpx.MockTransport(custom_handler),
    )
    text, filename = await client.export_activity("my_custom_key")
    assert text == MOCK_GPX_XML
    assert filename == "my_custom_key.gpx"


def test_make_mock_workout_factory():
    default_workout = make_mock_workout()
    assert default_workout["username"] == "mock_athlete"
    assert default_workout["workoutKey"] == "mock_custom_key_999"
    assert default_workout["description"] == "Afternoon Run"

    custom_workout = make_mock_workout(
        workoutKey="custom_123",
        description="Morning Intervals",
        totalDistance=10000.0,
    )
    assert custom_workout["workoutKey"] == "custom_123"
    assert custom_workout["description"] == "Morning Intervals"
    assert custom_workout["totalDistance"] == 10000.0


# ============================================================================
# 2. Exception Handling Tests
# ============================================================================


def test_exception_hierarchy():
    assert issubclass(SportsTrackerAuthenticationError, SportsTrackerError)
    assert issubclass(SportsTrackerNotFoundError, SportsTrackerError)
    assert issubclass(SportsTrackerAPIError, SportsTrackerError)


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_authentication_error(status_code: int):
    def auth_error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "Unauthorized"})

    client = SportsTrackerClient(
        session_key="bad-key",
        transport=httpx.MockTransport(auth_error_handler),
    )
    with pytest.raises(SportsTrackerAuthenticationError, match="Authentication failed"):
        await client.get_workouts()


@pytest.mark.asyncio
async def test_not_found_error():
    def not_found_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not Found"})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(not_found_handler),
    )
    with pytest.raises(SportsTrackerNotFoundError, match="Resource not found"):
        await client.get_workout_details("non_existent_key")


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [500, 502, 503])
async def test_server_status_error(status_code: int):
    def server_error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="Server error")

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(server_error_handler),
    )
    with pytest.raises(SportsTrackerAPIError, match="Sports Tracker API error"):
        await client.get_workouts()


@pytest.mark.asyncio
async def test_api_json_error_field():
    def api_error_payload_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "Rate limit exceeded"})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(api_error_payload_handler),
    )
    with pytest.raises(SportsTrackerAPIError, match="Rate limit exceeded"):
        await client.get_workouts()


@pytest.mark.asyncio
async def test_network_connection_error():
    def network_error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(network_error_handler),
    )
    with pytest.raises(SportsTrackerAPIError, match="Sports Tracker API request error"):
        await client.get_workouts()


@pytest.mark.asyncio
async def test_timeout_error():
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(timeout_handler),
    )
    with pytest.raises(SportsTrackerAPIError, match="Sports Tracker API request error"):
        await client.get_workouts()


# ============================================================================
# 4. In-Memory TTL Cache Tests
# ============================================================================


@pytest.mark.asyncio
async def test_client_cache_hit():
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"payload": [{"workoutKey": "cached_001"}]})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(counting_handler),
        cache_ttl=60.0,
    )

    # First call: cache miss, hits network
    res1 = await client.get_workouts(limit=10)
    assert call_count == 1
    assert res1 == [{"workoutKey": "cached_001"}]

    # Second call: cache hit, no network request
    res2 = await client.get_workouts(limit=10)
    assert call_count == 1
    assert res2 == [{"workoutKey": "cached_001"}]


@pytest.mark.asyncio
async def test_client_cache_miss_different_params():
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"payload": []})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(counting_handler),
        cache_ttl=60.0,
    )

    await client.get_workouts(limit=10)
    assert call_count == 1

    # Different parameters should produce different cache keys
    await client.get_workouts(limit=20)
    assert call_count == 2


@pytest.mark.asyncio
async def test_client_cache_expiration():
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"payload": []})

    # Short TTL of 50 milliseconds
    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(counting_handler),
        cache_ttl=0.05,
    )

    await client.get_workouts(limit=10)
    assert call_count == 1

    # Before TTL expires: hit
    await client.get_workouts(limit=10)
    assert call_count == 1

    # Wait for TTL to expire
    await asyncio.sleep(0.06)

    # After TTL expires: miss, re-fetches
    await client.get_workouts(limit=10)
    assert call_count == 2


@pytest.mark.asyncio
async def test_client_cache_force_refresh():
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"payload": []})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(counting_handler),
        cache_ttl=60.0,
    )

    await client.get_workouts(limit=10)
    assert call_count == 1

    # Force refresh bypasses cache
    await client.get_workouts(limit=10, force_refresh=True)
    assert call_count == 2


@pytest.mark.asyncio
async def test_client_clear_cache():
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"payload": []})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(counting_handler),
        cache_ttl=60.0,
    )

    await client.get_workouts(limit=10)
    assert call_count == 1

    client.clear_cache()

    # After clearing cache, should hit network again
    await client.get_workouts(limit=10)
    assert call_count == 2


@pytest.mark.asyncio
async def test_client_cache_disabled_with_zero_ttl():
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"payload": []})

    # TTL of 0 disables caching
    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(counting_handler),
        cache_ttl=0.0,
    )

    await client.get_workouts(limit=10)
    assert call_count == 1

    await client.get_workouts(limit=10)
    assert call_count == 2


@pytest.mark.asyncio
async def test_client_cache_does_not_cache_errors():
    def not_found_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Not found"})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(not_found_handler),
        cache_ttl=60.0,
    )

    with pytest.raises(SportsTrackerNotFoundError):
        await client.get_workout_details("non_existent_key")

    # Ensure no error entry was cached
    assert len(client._cache) == 0
