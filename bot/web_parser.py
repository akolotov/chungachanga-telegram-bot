from typing import Tuple, Optional, Dict, Callable
import logging
from bot.web_parsers import crc891, crhoy
from bot.web_parsers.helper import WebParserError, WebDownloadError
from bot.settings import settings

logger = logging.getLogger(__name__)

# Domain constants
CRC891_DOMAIN = "crc891.com"
CRHOY_DOMAIN = "www.crhoy.com"

# Headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Map domains to their parser functions
parsers: Dict[str, Callable] = {
    CRC891_DOMAIN: crc891.parse_article,
    CRHOY_DOMAIN: crhoy.parse_article,
}

def parse_article(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses an article from a given URL based on the domain.

    Args:
        url (str): The URL of the article to parse.

    Returns:
        Tuple[Optional[str], Optional[str]]: A tuple containing the article title and content.
        Returns (None, None) if any error occurs during parsing or if the domain is not supported.
    """
    try:
        for domain, parser_func in parsers.items():
            if domain in url:
                return parser_func(url, HEADERS)
        
        logger.error(f"Unsupported domain in URL: {url}")
        return None, None
    except (WebParserError, WebDownloadError, Exception) as e:
        if isinstance(e, WebDownloadError):
            logger.error(f"Failed to download article: {e}")
        elif isinstance(e, WebParserError):
            logger.error(f"Failed to parse article content: {e}")
        else:
            logger.error(f"Unexpected error while processing article: {e}")
        return None, None

if __name__ == "__main__":
    if len(settings.url_link) > 0:
        title, content = parse_article(settings.url_link)
        if title and content:
            print(f"\nTitle: {title}\n\nContent:\n{content}")
        else:
            print("Failed to extract content from the article.")
    else:
        print("URL_LINK environment variable is not set. Please set it in your environment or in a .env file.")