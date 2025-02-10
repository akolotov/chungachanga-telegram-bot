from bs4 import BeautifulSoup
from typing import Tuple
import logging
# import pyhtml2md
# import re
from markdownify import MarkdownConverter
from .helper import get_page_content, WebParserError, WebDownloadError

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
        WebDownloadError: If there's an error downloading the page.
    """
    try:
        content = get_page_content(url, headers)
    except WebDownloadError:
        # Re-raise download errors
        raise

    try:
        logger.info("Parsing the page content.")
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Determine if this is an opinion piece
        main_section = soup.find('section', class_='main-content')
        is_opinion = main_section and 'opinion' in ' '.join(main_section.get('class', []))
        
        if is_opinion:
            # Opinion piece format
            article = main_section.find('article', class_='articulo-opinion')
            if article:
                title = article.find('h1')
                content_div = article.find('div', class_='contenido')
                
                title_text = title.text.strip() if title else ""
                content_text = MarkdownConverter().convert_soup(content_div) if content_div else ""
        else:
            # Regular article format
            title = soup.find('h1', class_='titulo')
            content_div = soup.find('div', {'id': 'contenido'})
            
            title_text = title.text.strip() if title else ""
            
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

                    # # Replace closing blockquote tags with a newline after them
                    # main_content_str = str(main_content)
                    # main_content_str = re.sub(r'<blockquote>', '\n<div class="blockquote">\n<blockquote>\n', main_content_str, flags=re.IGNORECASE)
                    # main_content_str = re.sub(r'</blockquote>', '\n</blockquote>\n</div>\n', main_content_str, flags=re.IGNORECASE)
                    # # Remove spaces after opening tags and add space before them
                    # main_content_str = re.sub(r'<([^>]+)>\s+', r' <\1>', main_content_str)
                    # # Remove spaces before closing tags and add space after them
                    # main_content_str = re.sub(r'\s+</([^>]+)>', r'</\1> ', main_content_str)

                    # options = pyhtml2md.Options()
                    # options.splitLines = False
                    # converter = pyhtml2md.Converter(main_content_str, options)
                    # content_text = converter.convert()
                    content_text = MarkdownConverter().convert_soup(main_content)
                
            else:
                content_text = ""
        
        if not title_text or not content_text:
            raise WebParserError("Failed to extract title or content")
        
        logger.info(f"Successfully parsed the article with title '{title_text}'.")

        return title_text, content_text
    except Exception as e:
        logger.error(f"Error parsing article: {e}")
        raise WebParserError(f"Error parsing article: {e}") 