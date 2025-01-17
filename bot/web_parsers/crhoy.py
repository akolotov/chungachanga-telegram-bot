from bs4 import BeautifulSoup
from typing import Tuple
import logging
import pyhtml2md
import re
from .helper import get_page_content, WebParserError

logger = logging.getLogger(__name__)

def parse_article(url: str, headers: dict) -> Tuple[str, str]:
    """
    Parses a news article from the CRHoy website.

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
        
        # Extract title
        title = soup.find('h1', class_='titulo')
        title_text = title.text.strip() if title else ""
        
        # Extract main content
        content_div = soup.find('div', {'id': 'contenido'})
        if content_div:
            # Get main content div (usually the first div after optional bullet points)
            main_content = content_div.find('div', recursive=False)
            if main_content:
                # Remove unwanted elements
                unwanted_elements = [
                    'script', 'style', 'iframe',  # Technical elements
                    'div.banner-d', 'div.bannerEmbedsHome', 'div.moreBox',  # Ads and recommendations
                    'div.comentarios-container', 'div.etiquetas',  # Comments and tags
                    'div.leerMasOuter', 'div.gallery',  # "Read more" links
                    'div.wp-caption'
                ]
                
                for element in unwanted_elements:
                    for tag in main_content.select(element):
                        tag.decompose()

                # Replace closing blockquote tags with a newline after them
                main_content_str = str(main_content)
                main_content_str = re.sub(r'<blockquote>', '\n<blockquote>\n', main_content_str, flags=re.IGNORECASE)
                main_content_str = re.sub(r'</blockquote>', '\n</blockquote>\n', main_content_str, flags=re.IGNORECASE)
                # Remove spaces before closing tags and add space after them
                main_content_str = re.sub(r'\s+</([^>]+)>', r'</\1> ', main_content_str)

                options = pyhtml2md.Options()
                options.splitLines = False
                converter = pyhtml2md.Converter(main_content_str, options)
                content_text = converter.convert()
        else:
            content_text = ""
        
        if not title_text or not content_text:
            raise WebParserError("Failed to extract title or content")
        
        logger.info(f"Successfully parsed the article with title '{title_text}'.")

        return title_text, content_text
    except Exception as e:
        logger.error(f"Error parsing article: {e}")
        raise WebParserError(f"Error parsing article: {e}") 