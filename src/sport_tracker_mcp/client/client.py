import asyncio
import re
import time
from typing import Any

import httpx

from ..config import BASE_URL, SESSION_KEY


class SportsTrackerError(Exception):
    """Base class for SportsTracker exceptions"""

    pass


class SportsTrackerAuthenticationError(SportsTrackerError):
    """Raised when authentication fails"""

    pass


class SportsTrackerAPIError(SportsTrackerError):
    """Raised when the API returns an error"""

    pass


class SportsTrackerNotFoundError(SportsTrackerError):
    """Raised when a resource is not found"""

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
        self._cache: dict[str, tuple[float, Any]] = {}
        self.headers = {
            "STTAuthorization": session_key,
            "Accept": "application/json",
        }

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()

    def _make_cache_key(self, endpoint: str, params: dict | None = None) -> str:
        if not params:
            return endpoint
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}?{param_str}"

    async def get_workouts(
        self, limit: int = 50, offset: int = 0, force_refresh: bool = False
    ) -> list[dict]:
        params = {"limit": limit, "offset": offset, "sortonst": True}
        return (
            await self._get("/workouts", params=params, force_refresh=force_refresh)
            or []
        )

    async def get_workout_details(
        self, workout_key: str, force_refresh: bool = False
    ) -> dict:
        return (
            await self._get(
                f"/workouts/{workout_key}/combined", force_refresh=force_refresh
            )
            or {}
        )

    async def get_social_feed(
        self, limit: int = 10, offset: int = 0, force_refresh: bool = False
    ) -> list[dict]:
        params = {"limit": limit, "offset": offset}
        res = await self._get(
            "/user/feed/combined", params=params, force_refresh=force_refresh
        )
        if isinstance(res, list):
            return res
        if isinstance(res, dict):
            for key in ("feed", "items", "entries", "workouts"):
                if key in res and isinstance(res[key], list):
                    return res[key]
        return []

    async def get_user_stats(
        self, username: str | None = None, force_refresh: bool = False
    ) -> dict:
        if not username:
            user_info = await self.get_user_settings(force_refresh=force_refresh)
            username = user_info.get("username", "")
        return (
            await self._get(f"/workouts/{username}/stats", force_refresh=force_refresh)
            or {}
        )

    async def get_user_settings(self, force_refresh: bool = False):
        return await self._get("/user", force_refresh=force_refresh) or {}

    async def get_user_following(self, force_refresh: bool = False) -> dict:
        return await self._get("/user/follow", force_refresh=force_refresh) or {}

    async def get_routes(self, force_refresh: bool = False):
        return await self._get("/routes", force_refresh=force_refresh) or []

    async def get_route(self, route_id: str, force_refresh: bool = False) -> dict:
        return await self._get(f"/routes/{route_id}", force_refresh=force_refresh) or {}

    async def export_activity(self, workout_key: str) -> tuple[str, str]:
        async with self._create_httpx_session() as client:
            resp = await client.get(
                f"/workout/exportGpx/{workout_key}?token={self.session_key}"
            )
            resp.raise_for_status()

            filename = f"{workout_key}.gpx"
            disposition = resp.headers.get("content-disposition", "")
            match = re.search(r'filename="?([^";]+)"?', disposition)
            if match:
                filename = match.group(1)
            return resp.text, filename

    def _create_httpx_session(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers, transport=self.transport
        )

    async def _get(
        self,
        endpoint: str,
        params: dict | None = None,
        force_refresh: bool = False,
    ) -> Any:
        if not self.session_key:
            raise SportsTrackerAuthenticationError(
                "Authentication failed. STT_SESSION_KEY is empty or not set. Please set STT_SESSION_KEY in your .env or MCP client configuration."
            )

        cache_key = self._make_cache_key(endpoint, params)
        now = time.monotonic()

        if not force_refresh and self.cache_ttl > 0 and cache_key in self._cache:
            cached_time, cached_payload = self._cache[cache_key]
            if now - cached_time < self.cache_ttl:
                return cached_payload

        async with self._create_httpx_session() as client:
            try:
                resp = await client.get(endpoint, params=params)
                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, dict) and data.get("error"):
                    raise SportsTrackerAPIError(
                        f"Sports Tracker API error: {data['error']}"
                    )

                result = data.get("payload") if isinstance(data, dict) else data
                if self.cache_ttl > 0:
                    self._cache[cache_key] = (now, result)
                return result

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in (401, 403):
                    raise SportsTrackerAuthenticationError(
                        "Authentication failed. Check your session key."
                    )
                elif status == 404:
                    raise SportsTrackerNotFoundError(
                        f"Resource not found: {e.response.url}"
                    )
                else:
                    raise SportsTrackerAPIError(f"Sports Tracker API error: {e}")

            except httpx.HTTPError as e:
                raise SportsTrackerAPIError(f"Sports Tracker API request error: {e}")
