"""Config flow for the R6 Data Relay integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, override

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    R6DataRelayApiClient,
    R6DataRelayApiClientAuthError,
    R6DataRelayApiClientCommunicationError,
)
from .const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_VERIFY_SSL,
    DEFAULT_BASE_URL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    LOGGER,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Required(CONF_API_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)
STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class R6DataRelayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for R6 Data Relay."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step: base URL + shared token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {**user_input, CONF_BASE_URL: user_input[CONF_BASE_URL].rstrip("/")}
            self._async_abort_entries_match({CONF_BASE_URL: user_input[CONF_BASE_URL]})
            if (error := await self._validate(user_input)) is None:
                return self.async_create_entry(title=user_input[CONF_BASE_URL], data=user_input)
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_DATA_SCHEMA, user_input),
            errors=errors,
        )

    @override
    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Handle a reauthorization flow request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth: ask for a new token only."""
        errors: dict[str, str] = {}
        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            new_data = {**reauth_entry.data, CONF_API_TOKEN: user_input[CONF_API_TOKEN]}
            if (error := await self._validate(new_data)) is None:
                return self.async_update_reload_and_abort(reauth_entry, data=new_data)
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
        )

    async def _validate(self, data: dict[str, Any]) -> str | None:
        """Try listing teams with the given settings. Returns an error code or None."""
        client = R6DataRelayApiClient(
            data[CONF_BASE_URL],
            data[CONF_API_TOKEN],
            async_get_clientsession(
                self.hass, verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            ),
        )
        try:
            await client.async_list_teams()
        except R6DataRelayApiClientAuthError:
            LOGGER.warning("Relay at %s rejected the configured token", data[CONF_BASE_URL])
            return "invalid_auth"
        except R6DataRelayApiClientCommunicationError as err:
            LOGGER.warning("Could not reach relay at %s: %s", data[CONF_BASE_URL], err)
            return "cannot_connect"
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected error validating relay connection to %s", data[CONF_BASE_URL])
            return "unknown"
        return None
