"""Constants used across CRHoy crawler components."""

from zoneinfo import ZoneInfo


# Time zone constants
COSTA_RICA_TIMEZONE = ZoneInfo("America/Costa_Rica")
COSTA_RICA_UTC_OFFSET = "-06"  # Used in timestamp strings

# API endpoints
CRHOY_API_BASE_URL = "https://api.crhoy.net/"
CRHOY_WEBSITE_URL = "https://www.crhoy.com/"

# Spanish month names mapping
SPANISH_MONTH_MAP = {
    "enero": "01",
    "febrero": "02", 
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12"
} 