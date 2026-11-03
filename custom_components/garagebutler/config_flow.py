"""Config flow: paste the connection code from the GarageButler app."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_TOKEN, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import GarageButlerClient
from .const import CONF_CODE, DOMAIN, LOGGER
from .model import (
    AuthError,
    CannotConnect,
    Connection,
    GarageButlerError,
    InvalidCode,
    Snapshot,
    parse_connection_code,
)

SCHEMA = vol.Schema(
    {vol.Required(CONF_CODE): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))}
)


class GarageButlerConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry per GarageButler account."""

    VERSION = 1

    async def _check(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ) -> tuple[Connection, Snapshot] | None:
        """Read the code and fetch a snapshot; fills errors on failure."""
        try:
            connection = parse_connection_code(user_input[CONF_CODE])
            client = GarageButlerClient(async_get_clientsession(self.hass), connection)
            snapshot = Snapshot.from_json(await client.snapshot())
        except InvalidCode:
            errors["base"] = "invalid_code"
        except AuthError:
            errors["base"] = "invalid_auth"
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except GarageButlerError:
            LOGGER.exception("Unexpected answer from GarageButler")
            errors["base"] = "unknown"
        else:
            return connection, snapshot
        return None

    @staticmethod
    def _data(connection: Connection) -> dict[str, str]:
        return {
            CONF_URL: connection.url,
            CONF_API_KEY: connection.key,
            CONF_TOKEN: connection.token,
        }

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and (result := await self._check(user_input, errors)):
            connection, snapshot = result
            await self.async_set_unique_id(snapshot.user_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=snapshot.user_name or "GarageButler", data=self._data(connection)
            )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Token revoked: ask for a new code."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and (result := await self._check(user_input, errors)):
            connection, snapshot = result
            await self.async_set_unique_id(snapshot.user_id)
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data_updates=self._data(connection)
            )
        return self.async_show_form(step_id="reauth_confirm", data_schema=SCHEMA, errors=errors)
