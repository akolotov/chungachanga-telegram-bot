import requests
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class WebParserError(Exception):
    """Custom exception for WebParser errors."""
    pass

class WebDownloadError(WebParserError):
    """Exception raised when there's an error downloading the web page content."""
    pass

def get_page_content(url: str, headers: Dict[str, str]) -> str:
    """
    Fetches the content of a web page.

    Args:
        url (str): The URL of the web page to fetch.
        headers (Dict[str, str]): Headers to use for the request.

    Returns:
        str: The HTML content of the page.

    Raises:
        WebDownloadError: If there's an error fetching the page.
    """
    try:
        logger.info(f"Fetching page from {url}.")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch page: {e}")
        raise WebDownloadError(f"Failed to fetch page: {e}") 