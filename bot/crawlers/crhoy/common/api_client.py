"""HTTP client for CRHoy API."""

import json
from datetime import date
from typing import Any, Dict, Optional
import requests
from requests.exceptions import RequestException
import socket
from urllib.parse import urljoin

from .constants import CRHOY_API_BASE_URL, CRHOY_WEBSITE_URL
from .logger import get_component_logger

logger = get_component_logger("api_client")

# Constants
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_RETRIES = 3


class CRHoyAPIError(Exception):
    """Base exception for CRHoy API errors."""
    pass


class ConnectionError(CRHoyAPIError):
    """Raised when connection to CRHoy API fails."""
    pass


class APIResponseError(CRHoyAPIError):
    """Raised when API returns unexpected response."""
    pass


def check_internet_connection(timeout: float = 5) -> bool:
    """
    Check if there is an active internet connection.

    Args:
        timeout: Timeout in seconds for the connection check

    Returns:
        True if internet is available, False otherwise
    """
    try:
        # Try to connect to a reliable host (Google's DNS)
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False


def check_api_availability(timeout: float = DEFAULT_TIMEOUT) -> bool:
    """
    Check if CRHoy API is available.
    Any response from the server (even errors) indicates availability.
    Only connection errors indicate unavailability.

    Args:
        timeout: Request timeout in seconds

    Returns:
        True if API server responds (even with error), False if connection fails
    """
    try:
        requests.head(
            CRHOY_API_BASE_URL,
            timeout=timeout,
            allow_redirects=True
        )
        # Any response (even error) means server is up
        return True
    except RequestException:
        # Only connection errors mean server is down
        return False


def check_website_availability(timeout: float = DEFAULT_TIMEOUT) -> bool:
    """
    Check if CRHoy website is available.

    Args:
        timeout: Request timeout in seconds

    Returns:
        True if website is available, False otherwise
    """
    try:
        response = requests.head(
            CRHOY_WEBSITE_URL,
            timeout=timeout,
            allow_redirects=True
        )
        return response.status_code == 200
    except RequestException:
        return False


def fetch_news_metadata(
    target_date: date,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES
) -> Dict[str, Any]:
    """
    Fetch news metadata from CRHoy API for a specific date.

    Args:
        target_date: Date for which to fetch metadata
        timeout: Request timeout in seconds
        retries: Number of retries on failure

    Returns:
        Dictionary containing the news metadata

    Raises:
        ConnectionError: If connection to API fails
        APIResponseError: If API returns unexpected response
    """
    url = urljoin(CRHOY_API_BASE_URL, f"ultimas/{target_date.isoformat()}.json?v=3")
    
    for attempt in range(retries):
        try:
            logger.debug(f"Fetching metadata from {url} (attempt {attempt + 1}/{retries})")
            
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise APIResponseError(f"Invalid JSON response: {e}")
            
            # Validate response structure
            if not isinstance(data, dict) or "ultimas" not in data:
                raise APIResponseError("Unexpected response format")
            
            if not isinstance(data["ultimas"], list):
                raise APIResponseError("'ultimas' field is not a list")
            
            logger.info(
                f"Successfully fetched metadata for {target_date}. "
                f"Found {len(data['ultimas'])} news items."
            )
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Return empty metadata for dates with no news
                logger.warning(f"No metadata found for {target_date}")
                return {"ultimas": []}
            logger.warning(f"HTTP error fetching metadata: {e}")
            if attempt == retries - 1:
                raise ConnectionError(f"Failed to fetch metadata after {retries} attempts: {e}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching metadata: {e}")
            if attempt == retries - 1:
                raise ConnectionError(f"Failed to fetch metadata after {retries} attempts: {e}")
    
    raise ConnectionError(f"Failed to fetch metadata after {retries} attempts")
