"""Polls the GarageButler snapshot."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GarageButlerClient
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL
from .model import AuthError, GarageButlerError, Snapshot

type GarageButlerConfigEntry = ConfigEntry[GarageButlerCoordinator]


class GarageButlerCoordinator(DataUpdateCoordinator[Snapshot]):
    """One snapshot per config entry (= one GarageButler account)."""

    config_entry: GarageButlerConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: GarageButlerConfigEntry, client: GarageButlerClient
    ) -> None:
        super().__init__(
            hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.client = client

    async def _async_update_data(self) -> Snapshot:
        try:
            return Snapshot.from_json(await self.client.snapshot())
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GarageButlerError as err:
            raise UpdateFailed(str(err)) from err
