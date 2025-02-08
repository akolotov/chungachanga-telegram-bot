from sqlalchemy import Column, Integer, String, Boolean, Date, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import DATERANGE
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CRHoyNews(Base):
    __tablename__ = 'crhoy_news'

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    filename = Column(String)
    skipped = Column(Boolean, default=False, nullable=False)
    failed = Column(Boolean, default=False, nullable=False)

    categories = relationship("CRHoyNewsCategories", back_populates="news")

class CRHoyCategoriesCatalog(Base):
    __tablename__ = 'crhoy_categories_catalog'

    category = Column(String, primary_key=True)

    news_associations = relationship("CRHoyNewsCategories", back_populates="category_rel")

class CRHoyNewsCategories(Base):
    __tablename__ = 'crhoy_news_categories'

    news_id = Column(Integer, ForeignKey('crhoy_news.id'), primary_key=True)
    category = Column(String, ForeignKey('crhoy_categories_catalog.category'), primary_key=True)

    news = relationship("CRHoyNews", back_populates="categories")
    category_rel = relationship("CRHoyCategoriesCatalog", back_populates="news_associations")

class CRHoyMetadata(Base):
    __tablename__ = 'crhoy_metadata'

    date = Column(Date, primary_key=True)
    path = Column(String, nullable=False)

class MissedCRHoyMetadata(Base):
    __tablename__ = 'missed_crhoy_metadata'

    gap = Column(DATERANGE, primary_key=True)

    __table_args__ = (
        Index('ix_missed_crhoy_metadata_gap', gap, postgresql_using='gist'),
    )