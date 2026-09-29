"""Constants for the Royal Render integration."""
DOMAIN = "royalrender"
CONF_URL = "url"
CONF_API_KEY = "api_key"
PLATFORMS = ["sensor", "binary_sensor", "button"]
COMMANDS = {
    "enable": ("Enable", "mdi:play"),
    "disable": ("Disable (RR)", "mdi:pause"),
    "disable_after_frame": ("Disable after frame", "mdi:pause-circle-outline"),
    "working_hours": ("Use Working Hours", "mdi:calendar-clock"),
    "ignore_working_hours": ("Ignore Working Hours", "mdi:calendar-remove"),
}
