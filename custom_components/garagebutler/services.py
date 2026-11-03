"""Service garagebutler.update_mileage."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import DOMAIN
from .coordinator import GarageButlerConfigEntry
from .model import GarageButlerError

SERVICE_UPDATE_MILEAGE = "update_mileage"
ATTR_MILEAGE = "mileage"

UPDATE_MILEAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_MILEAGE): vol.All(vol.Coerce(int), vol.Range(min=0, max=9_999_999)),
    }
)


def _vehicle_of(hass: HomeAssistant, device_id: str) -> tuple[GarageButlerConfigEntry, str]:
    """Config entry and vehicle id of a GarageButler device."""
    vehicle_id = entry = None
    if device := dr.async_get(hass).async_get(device_id):
        vehicle_id = next((vid for domain, vid in device.identifiers if domain == DOMAIN), None)
        entry = next(
            (
                e
                for e in hass.config_entries.async_entries(DOMAIN)
                if e.entry_id in device.config_entries and e.state is ConfigEntryState.LOADED
            ),
            None,
        )
    if vehicle_id is None or entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_vehicle",
            translation_placeholders={"device_id": device_id},
        )
    return entry, vehicle_id


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the services of the integration."""

    async def update_mileage(call: ServiceCall) -> None:
        entry, vehicle_id = _vehicle_of(hass, call.data[ATTR_DEVICE_ID])
        coordinator = entry.runtime_data
        try:
            await coordinator.client.set_mileage(vehicle_id, call.data[ATTR_MILEAGE])
        except GarageButlerError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="api_error",
                translation_placeholders={"error": str(err)},
            ) from err
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_MILEAGE, update_mileage, schema=UPDATE_MILEAGE_SCHEMA
    )
