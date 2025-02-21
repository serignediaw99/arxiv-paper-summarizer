from pymongo import MongoClient
from config.settings import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION_NAME

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

def store_metadata(papers):
    """Stores paper metadata (including GCS URL) in MongoDB."""
    
    for paper in papers:
        document = {
            "paper_id": paper["paper_id"],
            "title": paper["title"],
            "gcs_url": paper["gcs_url"]
        }
        collection.update_one({"paper_id": paper["paper_id"]}, {"$set": document}, upsert=True)
        print(f"✅ Stored in MongoDB: {paper['title']} ({paper['paper_id']})")

    return True



