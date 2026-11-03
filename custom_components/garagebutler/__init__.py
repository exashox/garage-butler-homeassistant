"""GarageButler: vehicles, maintenance and ToDos in Home Assistant."""

from __future__ import annotations

from homeassistant.const import CONF_API_KEY, CONF_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from .api import GarageButlerClient
from .const import DOMAIN
from .coordinator import GarageButlerConfigEntry, GarageButlerCoordinator
from .model import Connection
from .services import async_setup_services

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR, Platform.TODO]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services once for all accounts."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GarageButlerConfigEntry) -> bool:
    """Set up one GarageButler account."""
    client = GarageButlerClient(
        async_get_clientsession(hass),
        Connection(entry.data[CONF_URL], entry.data[CONF_API_KEY], entry.data[CONF_TOKEN]),
    )
    coordinator = GarageButlerCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GarageButlerConfigEntry) -> bool:
    """Unload an account."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: GarageButlerConfigEntry, device: DeviceEntry
) -> bool:
    """Allow removing a vehicle device once the vehicle is gone or inactive."""
    vehicles = entry.runtime_data.data.vehicles
    return not any(domain == DOMAIN and vid in vehicles for domain, vid in device.identifiers)
