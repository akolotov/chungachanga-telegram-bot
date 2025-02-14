"""News analyzer functionality for CRHoy crawler."""

from pathlib import Path
from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.logger import get_component_logger
from ..common.models import CRHoyNews, CRHoySmartCategories, CRHoySummary, CRHoyNotifierNews
from ..common.utils import get_trigger_time_info
from ..common.constants import COSTA_RICA_TIMEZONE
from ..settings import settings
from .agent import categorize_article, summarize_article, ArticleRelation, UNKNOWN_CATEGORY
from bot.llm import BaseResponseError

logger = get_component_logger("downloader.news_analyzer")


class NewsAnalyzerError(Exception):
    """Raised when news analysis fails."""
    pass


def _get_smart_categories(session: Session) -> Dict[str, str]:
    """Get all smart categories and their descriptions, excluding the UNKNOWN_CATEGORY.
    
    Args:
        session: Database session
        
    Returns:
        Dictionary mapping category name to its description
    """
    query = select(CRHoySmartCategories).where(CRHoySmartCategories.category != UNKNOWN_CATEGORY)
    return {
        cat.category: cat.description
        for cat in session.execute(query).scalars().all()
    }


def _get_ignored_categories(session: Session) -> set[str]:
    """Get set of categories that should be ignored.
    
    Args:
        session: Database session
        
    Returns:
        Set of category names that should be ignored
    """
    query = select(CRHoySmartCategories).where(CRHoySmartCategories.ignore == True)  # noqa: E712
    return {cat.category for cat in session.execute(query).scalars().all()}


def _save_summary(
    news: CRHoyNews,
    lang: str,
    content: str,
    data_dir: Path
) -> str:
    """Save summary content to file.
    
    Args:
        news: News entry being analyzed
        lang: Language code for the summary
        content: Summary content to save
        data_dir: Base directory for storing data
        
    Returns:
        Path where summary was saved
        
    Raises:
        NewsAnalyzerError: If saving fails
    """
    try:
        # Convert timestamp to components
        dt = news.timestamp.astimezone()  # Use news timezone
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H-%M")
        
        # Construct path
        path = (
            data_dir / "news" / 
            date_str / 
            f"{time_str}-{news.id}-sum.{lang}.txt"
        )
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save content
        with path.open('w', encoding='utf-8') as f:
            f.write(content)
            
        logger.debug(f"Saved {lang} summary to {path}")
        return str(path)
        
    except Exception as e:
        raise NewsAnalyzerError(f"Failed to save {lang} summary: {e}")


def _prepare_summaries(
    news: CRHoyNews,
    content: str,
    data_dir: Path
) -> dict[str, CRHoySummary]:
    """Create, save, and prepare database records for news summaries.
    
    This function:
    1. Creates English summary and Russian translation using LLM
    2. Saves both summaries to files
    3. Prepares (but doesn't commit) database records for the summaries
    
    Args:
        news: News entry being analyzed
        content: Content of the news article
        data_dir: Base directory for storing data
        
    Returns:
        Dictionary mapping language codes to CRHoySummary records
        
    Raises:
        NewsAnalyzerError: If summary creation or saving fails
    """
    # Create summaries
    try:
        summary_result = summarize_article(content, "Russian")
        if isinstance(summary_result, BaseResponseError):
            raise NewsAnalyzerError(f"Summary creation failed: {summary_result.error}")
    except Exception as e:
        raise NewsAnalyzerError(f"Summary creation failed: {e}")
        
    # Save summaries and prepare records
    summaries = {}
    try:
        # Save English summary
        en_path = _save_summary(news, "en", summary_result.summary, data_dir)
        summaries["en"] = CRHoySummary(id=news.id, filename=en_path, lang="en")
        
        # Save Russian summary
        ru_path = _save_summary(news, "ru", summary_result.translated_summary, data_dir)
        summaries["ru"] = CRHoySummary(id=news.id, filename=ru_path, lang="ru")
        
    except Exception as e:
        raise NewsAnalyzerError(f"Failed to save summaries: {e}")
        
    return summaries


def analyze_news(
    news: CRHoyNews,
    session: Session,
    force: bool = False
) -> None:
    """Analyze a news article and update the database with results.
    
    This function:
    1. Checks if news is old enough to be analyzed
    2. Checks if news was already analyzed
    3. Categorizes the news using LLM
    4. If news should not be skipped:
       - Creates summaries in English and Russian
       - Saves summaries to files
       - Updates database with summary info
    5. Updates database with analysis results
    
    Args:
        news: News entry to analyze
        session: Database session to use
        force: If True, analyze news regardless of its age
        
    Raises:
        NewsAnalyzerError: If analysis fails unexpectedly
    """
    category_result = None  # Initialize to None to handle failures
    try:
        # Skip if news is too old (unless forced)
        if not force:
            trigger_info = get_trigger_time_info()
            if news.timestamp < trigger_info.previous:
                # Convert both timestamps to Costa Rica time for consistent logging
                news_cr_time = news.timestamp.astimezone(COSTA_RICA_TIMEZONE)
                prev_cr_time = trigger_info.previous.astimezone(COSTA_RICA_TIMEZONE)
                logger.debug(
                    f"Skipping news {news.id} as it's too old "
                    f"(news time: {news_cr_time}, previous trigger: {prev_cr_time})"
                )
                return
        
        # Check if already analyzed and has summaries
        existing = session.get(CRHoyNotifierNews, news.id)
        # if the news was failed, we should analyze it again even
        # if summaries already exist although such case should not happen
        # since summaries are stored in the database in the same transaction
        # with the news record
        if existing and not existing.failed:
            summaries = session.execute(
                select(CRHoySummary).where(CRHoySummary.id == news.id)
            ).scalars().all()
            if summaries:
                logger.info(f"News {news.id} already analyzed and has summaries")
                return
        
        # Read article content
        if not news.filename:
            raise NewsAnalyzerError(f"News {news.id} has no content file")
            
        try:
            with open(news.filename, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise NewsAnalyzerError(f"Failed to read news content: {e}")
        
        # Get categories info
        smart_categories = _get_smart_categories(session)
        ignored_categories = _get_ignored_categories(session)
        
        # Analyze category
        try:
            category_result = categorize_article(content, smart_categories)
            if isinstance(category_result, BaseResponseError):
                raise NewsAnalyzerError(f"Category analysis failed: {category_result.error}")
        except Exception as e:
            raise NewsAnalyzerError(f"Category analysis failed: {e}")
            
        # Add new category if needed in a separate transaction
        if category_result.category not in smart_categories:
            try:
                new_category = CRHoySmartCategories(
                    category=category_result.category,
                    description=category_result.category_description,
                    ignore=False
                )
                session.add(new_category)
                session.commit()
                logger.info(f"Added new category: {category_result.category}, description: {category_result.category_description}")
                
                # Update local cache of categories
                smart_categories[category_result.category] = category_result.category_description
                
            except Exception as e:
                session.rollback()
                raise NewsAnalyzerError(f"Failed to add new category: {e}")
            
        # Check if should be skipped
        should_skip = (
            category_result.related == ArticleRelation.NOT_APPLICABLE or
            category_result.category in ignored_categories
        )
        
        # Create notifier record
        notifier_news = CRHoyNotifierNews(
            id=news.id,
            timestamp=news.timestamp,
            related=category_result.related,
            category=category_result.category,
            skipped=should_skip,
            failed=False
        )
        
        if should_skip:
            # Just save notifier record and return
            session.merge(notifier_news)
            session.commit()
            logger.info(
                f"News {news.id} marked as skipped "
                f"(related: {category_result.related}, category: {category_result.category})"
            )
            return
            
        # Create and save summaries
        summaries = _prepare_summaries(news, content, settings.data_dir)
            
        # Update database in one transaction
        try:
            # Add all summaries
            for summary in summaries.values():
                session.add(summary)
            
            # Add notifier record
            session.merge(notifier_news)
            
            # Commit all changes
            session.commit()
            logger.info(f"Successfully analyzed news {news.id}")
            
        except Exception as e:
            session.rollback()
            raise NewsAnalyzerError(f"Failed to update database: {e}")
            
    except Exception as e:
        logger.error(f"Failed to analyze news {news.id}: {e}")
        
        # Update notifier record with failure
        try:
            # Use safe defaults if category_result is not available
            related = getattr(category_result, 'related', ArticleRelation.NOT_APPLICABLE) if category_result else ArticleRelation.NOT_APPLICABLE
            # Use UNKNOWN_CATEGORY for failed cases
            category = getattr(category_result, 'category', UNKNOWN_CATEGORY) if category_result else UNKNOWN_CATEGORY
            
            failed_news = CRHoyNotifierNews(
                id=news.id,
                timestamp=news.timestamp,
                related=related,
                category=category,
                skipped=False,
                failed=True
            )
            session.merge(failed_news)
            session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update failure status: {commit_error}")
            session.rollback()
            
        raise NewsAnalyzerError(str(e))


if __name__ == "__main__":
    import sys
    from ..common.db import db_session, init_db
    from ..settings import settings
    from bot.llm import initialize

    # Initialize LLM engine
    initialize()

    try:
        # Initialize database with URL from settings
        init_db(settings.database_url)
        
        # Get command line arguments
        force = "--force" in sys.argv

        with db_session() as session:
            # Find the most recent news that has content but hasn't been analyzed
            query = (
                select(CRHoyNews)
                .where(CRHoyNews.filename != "")  # Has content
                .where(CRHoyNews.failed == False)  # noqa: E712
                .where(CRHoyNews.skipped == False)  # noqa: E712
                .order_by(CRHoyNews.timestamp.desc())
                .limit(1)
            )
            
            news = session.execute(query).scalar_one_or_none()
            if not news:
                print("No unanalyzed news articles found", file=sys.stderr)
                sys.exit(1)

            print(f"\nAnalyzing most recent news:")
            print(f"ID: {news.id}")
            print(f"Timestamp: {news.timestamp.astimezone(COSTA_RICA_TIMEZONE)}")
            print(f"Filename: {news.filename}")
            print(f"Force: {force}")
            
            # Run analysis
            analyze_news(news, session, force)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1) 