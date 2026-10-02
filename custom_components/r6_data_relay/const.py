"""Constants for the R6 Data Relay integration."""

from datetime import timedelta
from logging import Logger, getLogger

DOMAIN = "r6_data_relay"
LOGGER: Logger = getLogger(__package__)

CONF_BASE_URL = "base_url"
CONF_API_TOKEN = "api_token"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_BASE_URL = "https://r6-data-relay.ault"
DEFAULT_VERIFY_SSL = True

# The relay refreshes upcoming/running matches every 3 minutes by default;
# polling it at the same cadence is cheap (it serves from an in-memory cache).
DEFAULT_SCAN_INTERVAL = timedelta(minutes=3)
