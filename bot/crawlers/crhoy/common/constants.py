"""Constants used across CRHoy crawler components."""

from zoneinfo import ZoneInfo


# Time zone constants
COSTA_RICA_TIMEZONE = ZoneInfo("America/Costa_Rica")
COSTA_RICA_UTC_OFFSET = "-06"  # Used in timestamp strings

# API endpoints
CRHOY_API_BASE_URL = "https://api.crhoy.net/"
CRHOY_WEBSITE_URL = "https://www.crhoy.com/site/dist/terminos_y_condiciones.html"

# HTTP headers for web requests
CRHOY_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

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