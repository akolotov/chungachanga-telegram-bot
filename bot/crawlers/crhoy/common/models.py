from sqlalchemy import Column, Integer, String, Boolean, Date, TIMESTAMP, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import DATERANGE
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CRHoyNews(Base):
    """Stores the main information about each news article from CRHoy.
    
    Fields:
        id (int): Primary key, matches the 'id' field from CRHoy's metadata API
        url (str): Full URL to the news article, matches the 'url' field from metadata
        timestamp (datetime): Combined date and hour from metadata with Costa Rica timezone 
                            (e.g., 2025-02-06 09:01:00-06)
        filename (str): Path to the markdown file containing the news content, 
                       null if not yet downloaded
        skipped (bool): True if news was filtered out due to being in ignored categories,
                       defaults to False
        failed (bool): True if attempt to parse the news content failed, 
                      defaults to False
    """

    __tablename__ = 'crhoy_news'

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    filename = Column(String)
    skipped = Column(Boolean, default=False, nullable=False)
    failed = Column(Boolean, default=False, nullable=False)

    categories = relationship("CRHoyNewsCategories", back_populates="news")

class CRHoyCategoriesCatalog(Base):
    """Catalog of all unique CRHoy news categories.
    
    Fields:
        category (str): Primary key, category name in URL-compatible format
                       (e.g., 'economia' or 'deportes/futbol')
    """
    __tablename__ = 'crhoy_categories_catalog'

    category = Column(String, primary_key=True)

    news_associations = relationship("CRHoyNewsCategories", back_populates="category_rel")

class CRHoyNewsCategories(Base):
    """Many-to-many relationship table linking news articles to their categories.
    
    Fields:
        news_id (int): Foreign key to CRHoyNews.id, part of composite primary key
        category (str): Foreign key to CRHoyCategoriesCatalog.category, 
                       part of composite primary key
    """
    __tablename__ = 'crhoy_news_categories'

    news_id = Column(Integer, ForeignKey('crhoy_news.id'), primary_key=True)
    category = Column(String, ForeignKey('crhoy_categories_catalog.category'), primary_key=True)

    news = relationship("CRHoyNews", back_populates="categories")
    category_rel = relationship("CRHoyCategoriesCatalog", back_populates="news_associations")

class CRHoyMetadata(Base):
    """Tracks which dates have had their metadata successfully downloaded.
    
    Fields:
        date (Date): Primary key, date for which metadata was downloaded at least once
        path (str): Path to the JSON file containing the downloaded metadata for this date
    """
    __tablename__ = 'crhoy_metadata'

    date = Column(Date, primary_key=True)
    path = Column(String, nullable=False)

class MissedCRHoyMetadata(Base):
    """Tracks date ranges (gaps) where metadata still needs to be downloaded.
    
    Fields:
        gap (DateRange): Primary key, represents a continuous range of dates where
                        metadata needs to be downloaded. The range is presented as an interval
                        [start_date, end_date) where start_date is included but end_date is 
                        excluded. Uses PostgreSQL's GiST index for efficient range queries.
    """
    __tablename__ = 'missed_crhoy_metadata'

    gap = Column(DATERANGE, primary_key=True)

    __table_args__ = (
        Index('ix_missed_crhoy_metadata_gap', gap, postgresql_using='gist'),
    )

class CRHoySmartCategories(Base):
    """Stores categories and their descriptions for news analyzer.
    
    Fields:
        category (str): Primary key, category name that could contain subcategory 
                       (e.g., 'economia' or 'deportes/futbol')
        description (str): Description of the category in English
        ignore (bool): If True, the news analyzer should not perform deep analysis 
                      of news in this category
    """
    __tablename__ = 'crhoy_smart_categories'

    category = Column(String, primary_key=True)
    description = Column(String, nullable=False)
    ignore = Column(Boolean, default=False, nullable=False)

class CRHoySummary(Base):
    """Stores summaries available for news articles.
    
    Fields:
        id (int): Foreign key to CRHoyNews.id, part of composite primary key
        filename (str): Path to the file with the summary of news
        lang (str): Language code of the summary (e.g., 'en', 'es', 'ru')
    """
    __tablename__ = 'crhoy_summary'

    id = Column(Integer, ForeignKey('crhoy_news.id'), primary_key=True)
    filename = Column(String, nullable=False)
    lang = Column(String(2), primary_key=True)  # 2-char language code

    news = relationship("CRHoyNews", backref="summaries")

class CRHoyNotifierNews(Base):
    """Stores analysis results for news articles.
    
    Fields:
        id (int): Foreign key to CRHoyNews.id, primary key
        timestamp (datetime): Same as the timestamp in CRHoyNews
        related (str): Whether the news is related to Costa Rica 
                      ('directly', 'indirectly', 'na')
        category (str): Foreign key to CRHoySmartCategories.category
        skipped (bool): True if news was filtered out due to category or 
                       not being related to Costa Rica
        failed (bool): True if news analysis failed
    """
    __tablename__ = 'crhoy_notifier_news'

    id = Column(Integer, ForeignKey('crhoy_news.id'), primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    related = Column(String, nullable=False)
    category = Column(
        String, 
        ForeignKey('crhoy_smart_categories.category'),
        nullable=False
    )
    skipped = Column(Boolean, default=False, nullable=False)
    failed = Column(Boolean, default=False, nullable=False)

    news = relationship("CRHoyNews", backref="notifier_analysis")
    smart_category = relationship("CRHoySmartCategories")

    __table_args__ = (
        CheckConstraint("related IN ('directly', 'indirectly', 'na')", name="ck_related_values"),
    )

class CRHoySentNews(Base):
    """Tracks which news articles have been sent to the Telegram channel.
    
    This table is used by the notifier bot to avoid sending duplicate news.
    Only recent sent news are kept - older records are cleaned up by the notifier bot
    based on the previous trigger time window.
    
    Fields:
        id (int): Foreign key to CRHoyNotifierNews.id, primary key
        timestamp (datetime): Original timestamp of the news article in Costa Rica timezone
    """
    __tablename__ = 'crhoy_sent_news'

    id = Column(Integer, ForeignKey('crhoy_notifier_news.id'), primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)

    notifier_news = relationship("CRHoyNotifierNews", backref="sent_status")
