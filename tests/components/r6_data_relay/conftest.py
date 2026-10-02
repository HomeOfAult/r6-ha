"""Fixtures for R6 Data Relay integration tests (shapes follow the relay's openapi.yaml)."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.r6_data_relay.const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
)

BASE_URL = "https://relay.test"
TOKEN = "test-token"
TEAMS_URL = f"{BASE_URL}/api/v1/teams"
MATCHES_URL = f"{BASE_URL}/api/v1/matches"

G2 = {"id": 1, "name": "G2 Esports", "acronym": "G2", "image_url": "https://img/g2.png"}
FAZE = {"id": 2, "name": "FaZe Clan", "acronym": "FaZe", "image_url": "https://img/faze.png"}
SPACESTATION = {"id": 3, "name": "Spacestation", "acronym": "SSG", "image_url": "https://img/ssg.png"}


def make_match(
    match_id: int,
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    *,
    status: str = "not_started",
    scheduled_at: str | None = None,
    end_at: str | None = None,
    winner_id: int | None = None,
) -> dict[str, Any]:
    """Build a Match as the relay serves it."""
    return {
        "id": match_id,
        "name": f"{team_a['acronym']} vs {team_b['acronym']}",
        "status": status,
        "scheduled_at": scheduled_at,
        "begin_at": scheduled_at,
        "end_at": end_at,
        "winner_id": winner_id,
        "league": {"id": 10, "name": "Six Invitational"},
        "serie": {"id": 11, "name": "2026"},
        "tournament": {"id": 12, "name": "Playoffs"},
        "opponents": [
            {"type": "Team", "opponent": team_a},
            {"type": "Team", "opponent": team_b},
        ],
    }


def envelope(data: Any) -> dict[str, Any]:
    """Wrap data in the relay's response envelope."""
    return {"data": data, "synced_at": "2026-10-02T12:00:00Z"}


def mock_relay(
    aioclient_mock: AiohttpClientMocker,
    *,
    teams: list[dict[str, Any]],
    upcoming: list[dict[str, Any]] | None = None,
    running: list[dict[str, Any]] | None = None,
    past: list[dict[str, Any]] | None = None,
) -> None:
    """Register relay responses for every endpoint the integration polls."""
    aioclient_mock.get(TEAMS_URL, json=envelope(teams))
    for status, matches in (("upcoming", upcoming), ("running", running), ("past", past)):
        aioclient_mock.get(f"{MATCHES_URL}?status={status}", json=envelope(matches or []))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading this custom component in every test."""
    return


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock relay config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=BASE_URL,
        data={CONF_BASE_URL: BASE_URL, CONF_API_TOKEN: TOKEN, CONF_VERIFY_SSL: True},
        unique_id=BASE_URL,
    )
