from bs4 import BeautifulSoup
from typing import Tuple
import logging
from .helper import get_page_content, WebParserError

logger = logging.getLogger(__name__)

def parse_article(url: str, headers: dict) -> Tuple[str, str]:
    """
    Parses a news article from the CRC891 website.

    Args:
        url (str): The URL of the article to parse.
        headers (dict): Headers to use for the request.

    Returns:
        Tuple[str, str]: A tuple containing the article title and content.

    Raises:
        WebParserError: If there's an error parsing the article.
    """
    try:
        content = get_page_content(url, headers)

        logger.info("Parsing the page content.")
        soup = BeautifulSoup(content, 'html.parser')

        title = soup.find('h1', class_='post-title entry-title')
        title_text = title.text.strip() if title else ""

        content_div = soup.find('div', class_='entry-content entry clearfix')
        
        if content_div:
            for unwanted in content_div.find_all(['div', 'script', 'style', 'figure']):
                unwanted.decompose()
            content_text = content_div.get_text(separator='\n', strip=True)
        else:
            content_text = ""

        if not title_text or not content_text:
            raise WebParserError("Failed to extract title or content")
        
        logger.info(f"Successfully parsed the article with title '{title_text}'.")

        return title_text, content_text
    except Exception as e:
        logger.error(f"Error parsing article: {e}")
        raise WebParserError(f"Error parsing article: {e}") 