import requests
from bs4 import BeautifulSoup
from typing import Tuple, Optional
from dotenv import load_dotenv
import logging
from settings import settings

logger = logging.getLogger(__name__)

class WebParserError(Exception):
    """Custom exception for WebParser errors."""
    pass

class WebParser:
    """A class to parse news articles from specific websites."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_page_content(self, url: str) -> str:
        """
        Fetches the content of a web page.

        Args:
            url (str): The URL of the web page to fetch.

        Returns:
            str: The HTML content of the page.

        Raises:
            WebParserError: If there's an error fetching the page.
        """
        try:
            logger.info(f"Fetching page from {url}.")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page: {e}")
            raise WebParserError(f"Failed to fetch page: {e}")

    def parse_crc891_article(self, url: str) -> Tuple[str, str]:
        """
        Parses a news article from the CRC891 website.

        Args:
            url (str): The URL of the article to parse.

        Returns:
            Tuple[str, str]: A tuple containing the article title and content.

        Raises:
            WebParserError: If there's an error parsing the article.
        """
        try:
            content = self.get_page_content(url)

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

def parse_article(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses an article from a given URL.

    Args:
        url (str): The URL of the article to parse.

    Returns:
        Tuple[Optional[str], Optional[str]]: A tuple containing the article title and content,
        or (None, None) if parsing fails.
    """
    parser = WebParser()
    try:
        return parser.parse_crc891_article(url)
    except WebParserError as e:
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