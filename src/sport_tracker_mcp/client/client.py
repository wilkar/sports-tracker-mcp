from typing import Any

import httpx
from cachetools import TTLCache

from ..config import BASE_URL, SESSION_KEY


class SportsTrackerError(Exception):
    """Base class for SportsTracker exceptions."""

    pass


class SportsTrackerNotFoundError(SportsTrackerError):
    """Raised when a resource is not found."""

    pass


class SportsTrackerClient:
    def __init__(
        self,
        session_key: str = SESSION_KEY,
        base_url: str = BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
        cache_ttl: float = 60.0,
    ):
        self.base_url = base_url
        self.session_key = session_key
        self.transport = transport
        self.cache_ttl = cache_ttl
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=256, ttl=cache_ttl)
        self.headers = {
            "STTAuthorization": session_key,
            "Accept": "application/json",
        }

    def _make_cache_key(self, endpoint: str, params: dict | None = None) -> str:
        if not params:
            return endpoint
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}?{param_str}"

    async def get_workouts(self, limit: int = 50, offset: int = 0) -> list[dict]:
        params = {"limit": limit, "offset": offset, "sortonst": True}
        return await self._get("/workouts", params=params) or []

    async def get_workout_details(self, workout_key: str) -> dict:
        return await self._get(f"/workouts/{workout_key}/combined") or {}

    async def get_social_feed(self, limit: int = 10, offset: int = 0) -> list[dict]:
        params = {"limit": limit, "offset": offset}
        res = await self._get("/user/feed/combined", params=params)
        if isinstance(res, list):
            return res
        if isinstance(res, dict):
            for key in ("feed", "items", "entries", "workouts"):
                if key in res and isinstance(res[key], list):
                    return res[key]
        return []

    async def get_user_stats(self, username: str | None = None) -> dict:
        if not username:
            user_info = await self.get_user_settings()
            username = user_info.get("username", "")
        return await self._get(f"/workouts/{username}/stats") or {}

    async def get_user_settings(self) -> dict:
        return await self._get("/user") or {}

    def _create_httpx_session(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, transport=self.transport
        )

    async def _get(
        self,
        endpoint: str,
        params: dict | None = None,
    ) -> Any:
        if not self.session_key:
            raise SportsTrackerError(
                "Authentication failed. STT_SESSION_KEY is empty or not set. Please set STT_SESSION_KEY in your .env or MCP client configuration."
            )

        cache_key = self._make_cache_key(endpoint, params)
        if cache_key in self._cache:
            return self._cache[cache_key]

        async with self._create_httpx_session() as client:
            try:
                resp = await client.get(endpoint, params=params)
                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, dict) and data.get("error"):
                    raise SportsTrackerError(
                        f"Sports Tracker API error: {data['error']}"
                    )

                result = data.get("payload") if isinstance(data, dict) else data
                self._cache[cache_key] = result
                return result

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in (401, 403):
                    raise SportsTrackerError(
                        "Authentication failed. Check your session key."
                    )
                elif status == 404:
                    raise SportsTrackerNotFoundError(
                        f"Resource not found: {e.response.url}"
                    )
                else:
                    raise SportsTrackerError(f"Sports Tracker API error: {e}")

            except httpx.HTTPError as e:
                raise SportsTrackerError(f"Sports Tracker API request error: {e}")
