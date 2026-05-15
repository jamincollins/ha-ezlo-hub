from homeassistant.const import Platform

DOMAIN = "ezlo"

PLATFORMS = [Platform.SWITCH, Platform.LOCK, Platform.COVER, Platform.SENSOR]

# Config entry keys
CONF_HUB_SERIAL = "hub_serial"
CONF_HUB_UUID = "hub_uuid"
CONF_HUB_USER = "hub_user"
CONF_HUB_TOKEN = "hub_token"

# Vera/Ezlo cloud
VERA_AUTH_URL = "https://vera-us-oem-autha11.mios.com/autha/auth/username/{}"
VERA_AUTH_URL_ALT = "https://vera-us-oem-autha12.mios.com/autha/auth/username/{}"
VERA_SHA1_SALT = "oZ7QE6LcLJp6fiWzdqZc"
JWT_EXCHANGE_URL = "https://cloud.ezlo.com/mca-router/token/exchange/legacy-to-cloud"
ACCESS_KEYS_URL = "https://api-cloud.ezlo.com/v1/request"

# Hub local connection
HUB_PORT = 17000
HUB_TLS_CIPHER = "AES256-SHA256"
RECONNECT_DELAY = 10
REQUEST_TIMEOUT = 10
PING_INTERVAL = 60

# Device type identifiers returned by the hub
DEV_TYPE_SWITCH = "switch.inwall"
DEV_TYPE_DOORLOCK = "doorlock"
DEV_TYPE_GARAGE = "shutter.garage"

# Item names
ITEM_SWITCH = "switch"
ITEM_DOOR_LOCK = "door_lock"
ITEM_BATTERY = "battery"
ITEM_BATTERY_MAINT = "battery_maintenance_state"
ITEM_GARAGE_DOOR = "garage_door"
ITEM_BARRIER_STATE = "barrier_state"

# Device types this integration handles; anything else is logged as unsupported.
SUPPORTED_DEVICE_TYPES = {DEV_TYPE_SWITCH, DEV_TYPE_DOORLOCK, DEV_TYPE_GARAGE}
