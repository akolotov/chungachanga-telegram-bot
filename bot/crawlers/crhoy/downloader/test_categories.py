from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from bot.crawlers.crhoy.downloader.news_analyzer import _get_smart_categories
from bot.crawlers.crhoy.settings import settings

# Create database connection
engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)

# Create a session and get categories
with Session() as session:
    categories = _get_smart_categories(session)
    
    # Print formatted JSON
    print(json.dumps(categories, indent=2, ensure_ascii=False)) 