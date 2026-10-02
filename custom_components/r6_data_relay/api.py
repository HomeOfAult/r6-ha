"""Async client for the r6-data-relay /api/v1 HTTP API.

Deliberately framework-light (no Home Assistant imports) so it can be
unit-tested with a plain aiohttp.ClientSession.
"""

from __future__ import annotations

from typing import Any

import aiohttp


class R6DataRelayApiClientError(Exception):
    """Base error for the relay API client."""


class R6DataRelayApiClientAuthError(R6DataRelayApiClientError):
    """Raised when the relay rejects the configured bearer token."""


class R6DataRelayApiClientCommunicationError(R6DataRelayApiClientError):
    """Raised when the relay can't be reached or returns an unexpected response."""


class R6DataRelayApiClient:
    """Thin wrapper around the read-only parts of the relay API."""

    def __init__(self, base_url: str, token: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._session = session

    async def async_list_teams(self) -> list[dict[str, Any]]:
        """Return the teams currently enabled for tracking, with rosters."""
        return await self._get_data("/api/v1/teams")

    async def async_list_matches(self, status: str) -> list[dict[str, Any]]:
        """Return cached matches for all enabled teams (upcoming|running|past)."""
        return await self._get_data("/api/v1/matches", params={"status": status})

    async def _get_data(self, path: str, *, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """GET a path and unwrap the {"data": ..., "synced_at": ...} envelope."""
        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with self._session.get(url, headers=headers, params=params) as response:
                if response.status in (401, 403):
                    raise R6DataRelayApiClientAuthError(f"GET {path} returned {response.status}")
                if response.status >= 400:
                    raise R6DataRelayApiClientCommunicationError(
                        f"GET {path} returned {response.status}"
                    )
                body = await response.json()
        except R6DataRelayApiClientError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise R6DataRelayApiClientCommunicationError(f"GET {path} failed: {err}") from err

        if not isinstance(body, dict):
            raise R6DataRelayApiClientCommunicationError(f"GET {path} returned an unexpected body")
        # The relay's team-filtered match path can emit null instead of [].
        return body.get("data") or []
