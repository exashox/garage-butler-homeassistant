"""Constants for the GarageButler integration."""

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final = "garagebutler"
LOGGER = logging.getLogger(__package__)

CONF_CODE: Final = "code"

UPDATE_INTERVAL = timedelta(minutes=15)
