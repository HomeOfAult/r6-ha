"""Tests for the R6 Data Relay config flow."""

from __future__ import annotations

import aiohttp
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.r6_data_relay.const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
)

from .conftest import BASE_URL, TEAMS_URL, TOKEN, envelope

USER_INPUT = {CONF_BASE_URL: BASE_URL, CONF_API_TOKEN: TOKEN, CONF_VERIFY_SSL: False}


async def _start_user_flow(hass: HomeAssistant, user_input: dict) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_user_flow_success(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Valid settings create an entry; a trailing slash on the URL is dropped."""
    aioclient_mock.get(TEAMS_URL, json=envelope([]))

    result = await _start_user_flow(hass, {**USER_INPUT, CONF_BASE_URL: BASE_URL + "/"})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == USER_INPUT


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A connection failure surfaces as cannot_connect."""
    aioclient_mock.get(TEAMS_URL, exc=aiohttp.ClientConnectionError("boom"))

    result = await _start_user_flow(hass, USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_invalid_auth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 401 surfaces as invalid_auth."""
    aioclient_mock.get(TEAMS_URL, status=401)

    result = await _start_user_flow(hass, USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Adding the same relay twice aborts."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(TEAMS_URL, json=envelope([]))

    result = await _start_user_flow(hass, USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A successful reauth stores the new token."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(TEAMS_URL, json=envelope([]))

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_TOKEN: "new-token"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_TOKEN] == "new-token"


async def test_reauth_flow_invalid_auth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A bad token during reauth redisplays the form."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(TEAMS_URL, status=401)

    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_TOKEN: "bad-token"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
