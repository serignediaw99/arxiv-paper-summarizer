from fastapi import FastAPI, Query
from pymongo import MongoClient
from typing import List
from arxiv_paper_summarizer.summarization import relevance_analyzer  # Import your script to use for relevance checking
import os

# Initialize FastAPI app
app = FastAPI()

# Connect to MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "arxiv_papers")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "arxiv_papers.papers_metadata")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

@app.get("/search")
def search_papers(keywords: List[str] = Query(...)):
    """
    Endpoint to search for research papers based on topic keywords.
    """
    # Use relevance analyzer to find relevant paper IDs
    relevant_papers = relevance_analyzer.find_relevant_papers(keywords, limit=10)

    # Extract paper_ids
    paper_ids = [paper["paper_id"] for paper in relevant_papers]
    
    # Query MongoDB for those papers
    results = list(collection.find({"paper_id": {"$in": paper_ids}}, {"_id": 0}))
    
    return {"papers": results}

# Run with: uvicorn main:app --reload