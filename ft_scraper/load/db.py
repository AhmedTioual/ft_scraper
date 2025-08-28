from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from pymongo.collection import Collection
from typing import Optional
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

def get_db_connection(
    uri=os.getenv("DB_URL"),
    db_name="news_scraper",
    collection_name="articles"
):
    """
    Connect to MongoDB Atlas and return the collection object.

    Args:
        uri (str): MongoDB Atlas connection URI
        db_name (str): Database name
        collection_name (str): Collection name

    Returns:
        collection (pymongo.collection.Collection) or None if connection fails
    """
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.server_info()  # forces connection check
        db = client[db_name]
        collection = db[collection_name]

        # Ensure article_id is unique
        collection.create_index("article_id", unique=True)
        print("Connected to MongoDB Atlas!")
        return collection

    except ConnectionFailure as e:
        print(f"Could not connect to MongoDB Atlas: {e}")
        return None

def insert_article(collection, article: dict):
    """
    Insert a single article into the MongoDB Atlas collection.

    Args:
        collection: MongoDB collection object
        article (dict): Article data

    Returns:
        inserted_id or None if error
    """
    if collection is None:
        print("No database connection.")
        return None

    try:
        result = collection.insert_one(article)
        print(f"Article inserted with _id: {result.inserted_id}")
        return result.inserted_id

    except DuplicateKeyError:
        print("Article already exists (duplicate article_id). Skipping insert.")
        return None

    except Exception as e:
        print(f"Failed to insert article: {e}")
        return None

def get_latest_published_at_by_category(
    collection: Collection, category: str
) -> Optional[datetime]:
    """
    Fetch the most recent published_at date in a given category.

    Args:
        collection (pymongo.collection.Collection): MongoDB collection object
        category (str): Category name (e.g., "global-economy")

    Returns:
        datetime or None: The latest published_at value
    """
    if collection is None:
        print("No database connection.")
        return None

    try:
        result = (
            collection.find({"category": category}, {"published_at": 1, "_id": 0})
            .sort("published_at", -1)  # sort descending by date
            .limit(1)
        )

        doc = next(result, None)
        if doc and "published_at" in doc:
            print(f"Latest published_at for '{category}': {doc['published_at']}")
            return doc["published_at"]

        print(f"No published_at found for category '{category}'.")
        return None

    except Exception as e:
        print(f"Error fetching latest published_at: {e}")
        return None
    
def load_articles(collection):
    try:
        # Load articles
        articles = list(collection.find({}, {
            "article_id": 1,
            "topper__headline": 1,
            "standfirst": 1,
            "content": 1,
            "byline": 1,
            "published_at": 1,
            "media": 1,
            "section": 1,
            "category": 1
        }))
        return articles

    except Exception as e:
        print(f"Error fetching articles : {e}")
        return None

def get_recent_articles(collection):
    try:
        # Time 24 hours ago (timezone-aware)
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)

        # Query recent articles that have non-empty content
        recent_articles = list(collection.find(
            {
                "published_at": {"$gte": cutoff.isoformat()},
                "content": { "$not": { "$size": 0 } }
            },
            {"article_id": 1, "topper__headline": 1, "content": 1}
        ))

        return recent_articles

    except Exception as e:
        print(f"Error fetching articles: {e}")
        return None

def get_distinct_themes(collection):
    
    try:
        # Get distinct themes
        distinct_themes = collection.distinct("topper__primary_theme")

        print(f"Found {len(distinct_themes)} distinct themes:")
        print(distinct_themes)
    except:
        pass