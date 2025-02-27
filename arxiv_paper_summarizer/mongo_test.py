from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get MongoDB URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "arxiv_papers")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "papers_metadata")

print(f"Connecting to MongoDB using URI: {MONGO_URI}")
print(f"Looking for database: {MONGO_DB_NAME}")
print(f"Looking for collection: {MONGO_COLLECTION_NAME}")

try:
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    
    # Test connection by listing all database names
    print("\nAvailable databases:")
    for db_name in client.list_database_names():
        print(f"- {db_name}")
    
    # Connect to the specified database
    db = client[MONGO_DB_NAME]
    
    # List all collections in this database
    print(f"\nCollections in '{MONGO_DB_NAME}' database:")
    for collection_name in db.list_collection_names():
        print(f"- {collection_name}")
    
    # Try to access the specified collection
    collection = db[MONGO_COLLECTION_NAME]
    
    # Count documents
    count = collection.count_documents({})
    print(f"\nFound {count} documents in {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")
    
    # If documents exist, show a sample
    if count > 0:
        sample = collection.find_one({})
        print("\nSample document fields:")
        for key in sample.keys():
            value = sample[key]
            # Truncate long values for display
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            print(f"- {key}: {value}")
    else:
        print("\nNo documents found in this collection.")
        
        # Check if there might be a collection name issue
        for alt_collection in db.list_collection_names():
            alt_count = db[alt_collection].count_documents({})
            if alt_count > 0:
                print(f"However, found {alt_count} documents in alternative collection: {alt_collection}")
                sample = db[alt_collection].find_one({})
                print("Sample document fields:")
                print(list(sample.keys()))
                break
    
except Exception as e:
    print(f"\nError connecting to MongoDB: {str(e)}")
    
    # Additional error details for common issues
    if "Authentication failed" in str(e):
        print("\nThis appears to be an authentication error. Check your username and password in the MongoDB URI.")
    elif "timed out" in str(e):
        print("\nConnection timed out. Check your network configuration and make sure your IP is in the MongoDB Atlas whitelist.")
    elif "SSL" in str(e):
        print("\nSSL/TLS error. This might be related to your network configuration or MongoDB Atlas requirements.")