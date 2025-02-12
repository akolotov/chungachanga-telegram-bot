from sqlalchemy import Column, Integer, String, Boolean, Date, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import DATERANGE
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CRHoyNews(Base):
    """Stores the main information about each news article from CRHoy.
    
    Fields:
        id (int): Primary key, matches the 'id' field from CRHoy's metadata API
        url (str): Full URL to the news article, unique, matches the 'url' field from metadata
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
    url = Column(String, unique=True, nullable=False)
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