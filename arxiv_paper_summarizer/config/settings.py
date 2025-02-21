import os
from dotenv import load_dotenv

# Load environment variables from a .env file (if using)
load_dotenv()

# Function to get config from either Airflow Variables or environment variables
def get_config(key, default=None):
    try:
        from airflow.models import Variable
        return Variable.get(key, default_var=os.getenv(key, default))
    except ImportError:
        return os.getenv(key, default)


# Google Cloud Storage Configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCP_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME")

# RSS Feed URL for Arxiv AI Papers
ARXIV_RSS_FEED = get_config("ARXIV_RSS_FEED", "https://rss.arxiv.org/rss/cs.ai")
