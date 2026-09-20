import asyncio

import httpx
import pytest

from sport_tracker_mcp.client import (
    SportsTrackerClient,
    SportsTrackerError,
    SportsTrackerNotFoundError,
)
from tests.fixtures import (
    MOCK_USER_FEED_PAYLOAD,
    MOCK_USER_SETTINGS_PAYLOAD,
    MOCK_USER_STATS_PAYLOAD,
    MOCK_WORKOUT_DETAILS_PAYLOAD,
    MOCK_WORKOUTS_PAYLOAD,
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
    feed = await client.get_social_feed(limit=10)
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


# ============================================================================
# 2. Exception Handling Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_authentication_error(status_code: int):
    def auth_error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "Unauthorized"})

    client = SportsTrackerClient(
        session_key="bad-key",
        transport=httpx.MockTransport(auth_error_handler),
    )
    with pytest.raises(SportsTrackerError, match="Authentication failed"):
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
    with pytest.raises(SportsTrackerError, match="Sports Tracker API error"):
        await client.get_workouts()


@pytest.mark.asyncio
async def test_api_json_error_field():
    def api_error_payload_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "Rate limit exceeded"})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(api_error_payload_handler),
    )
    with pytest.raises(SportsTrackerError, match="Rate limit exceeded"):
        await client.get_workouts()


@pytest.mark.asyncio
async def test_network_connection_error():
    def network_error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(network_error_handler),
    )
    with pytest.raises(SportsTrackerError, match="Connection refused"):
        await client.get_workouts()


@pytest.mark.asyncio
async def test_timeout_error():
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(timeout_handler),
    )
    with pytest.raises(SportsTrackerError, match="Sports Tracker API request error"):
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
async def test_client_cache_maxsize_eviction():
    from cachetools import TTLCache

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"payload": []})
        ),
        cache_ttl=60.0,
    )
    # Reconfigure cache with a small maxsize of 2 for testing eviction
    client._cache = TTLCache(maxsize=2, ttl=60.0)

    await client.get_workouts(limit=10)
    await client.get_workouts(limit=20)
    assert len(client._cache) == 2

    # A 3rd distinct endpoint/param evicts the least recently used entry
    await client.get_workouts(limit=30)
    assert len(client._cache) == 2
    assert (
        client._make_cache_key(
            "/workouts", {"limit": 10, "offset": 0, "sortonst": True}
        )
        not in client._cache
    )
    assert (
        client._make_cache_key(
            "/workouts", {"limit": 30, "offset": 0, "sortonst": True}
        )
        in client._cache
    )


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


@pytest.mark.asyncio
async def test_client_sanitizes_non_dict_payload():
    def malformed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"payload": [{"workoutKey": "w1"}, "not a dict", None, 123]},
        )

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(malformed_handler),
    )
    workouts = await client.get_workouts()
    assert len(workouts) == 1
    assert workouts[0]["workoutKey"] == "w1"


@pytest.mark.asyncio
async def test_get_workout_details_encodes_path_and_query_injection() -> None:
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, json={"payload": {"workoutKey": "ok"}})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(handler),
    )

    # 1. Path traversal attempt is safely percent-encoded
    await client.get_workout_details("../../../user")
    assert requested_urls[-1].endswith("/workouts/..%2F..%2F..%2Fuser/combined")
    assert "/user/combined" not in requested_urls[-1]

    # 2. Query injection attempt is safely percent-encoded
    await client.get_workout_details("a?limit=9999")
    assert requested_urls[-1].endswith("/workouts/a%3Flimit%3D9999/combined")
    assert "?limit=9999" not in requested_urls[-1]


@pytest.mark.asyncio
async def test_get_user_stats_encodes_username() -> None:
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, json={"payload": {"totalWorkouts": 5}})

    client = SportsTrackerClient(
        session_key="mock-key",
        transport=httpx.MockTransport(handler),
    )

    await client.get_user_stats("attacker/admin?grant=true")
    assert requested_urls[-1].endswith(
        "/workouts/attacker%2Fadmin%3Fgrant%3Dtrue/stats"
    )
    assert "?grant=true" not in requested_urls[-1]
