import os
import re
import argparse
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from dotenv import load_dotenv

# Import from our modules
from summarization.ollama_client import query_ollama
from summarization.text_processor import prepare_text_for_llm

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "arxiv_papers")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "arxiv_papers.papers_metadata")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

def get_papers_without_summary(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve papers that have extracted text but no summary.
    
    Args:
        limit: Maximum number of papers to retrieve
        
    Returns:
        List of paper documents from MongoDB
    """
    papers = collection.find(
        {
            "extracted_text": {"$exists": True},
            "summary": {"$exists": False}
        },
        {
            "paper_id": 1, 
            "title": 1, 
            "extracted_text": 1
        }
    ).limit(limit)
    
    return list(papers)

def generate_summary(
    title: str, 
    text: str, 
    model: str = DEFAULT_MODEL
) -> str:
    """
    Use LLM to generate a concise summary of the paper.
    
    Args:
        title: The paper title
        text: The extracted text from the PDF
        model: Ollama model to use
    
    Returns:
        Generated summary
    """
    # Process text to focus on important sections and fit within context window
    processed_text = prepare_text_for_llm(text, max_length=8000)
    
    prompt = f"""
    You are an AI research assistant tasked with summarizing research papers accurately.
    
    PAPER TITLE: {title}
    
    PAPER CONTENT (extracted from key sections):
    {processed_text}
    
    Please provide a concise summary of this research paper with the following structure:
    
    1. OBJECTIVE: In 1-2 sentences, what is the paper trying to accomplish?
    2. METHODS: In 2-3 sentences, what methods or approaches did the authors use?
    3. RESULTS: In 2-3 sentences, what were the main findings or results?
    4. SIGNIFICANCE: In 1-2 sentences, why does this matter to the field?
    5. KEY INSIGHTS: Bullet list of 3-5 key takeaways or insights from the paper.
    
    Keep the total summary under 500 words.
    """
    
    # Query Ollama with higher max tokens for the summary
    summary = query_ollama(prompt, model=model, max_tokens=1000, temperature=0.1)
    
    return summary.strip()

def update_paper_with_summary(
    paper_id: str, 
    summary: str
) -> bool:
    """
    Update MongoDB with the paper summary.
    
    Args:
        paper_id: ID of the paper in MongoDB
        summary: Generated summary text
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        result = collection.update_one(
            {"paper_id": paper_id},
            {"$set": {
                "summary": summary
            }}
        )
        
        if result.modified_count == 1:
            print(f"✅ Updated MongoDB with summary for {paper_id}")
            return True
        else:
            print(f"⚠️ No documents matched or updated for {paper_id}")
            return False
    except Exception as e:
        print(f"❌ Error updating MongoDB: {str(e)}")
        return False

def summarize_papers(
    limit: int = 5,
    model: str = DEFAULT_MODEL,
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Process papers that have text extracted but no summary yet.
    
    Args:
        limit: Maximum number of papers to process
        model: LLM model to use
        force_update: If True, re-summarize papers even if they already have summaries
        
    Returns:
        Dictionary with summarization results
    """
    # Query appropriate papers
    if force_update:
        # Find papers with extracted text, regardless of summary status
        papers = collection.find(
            {"extracted_text": {"$exists": True}},
            {"paper_id": 1, "title": 1, "extracted_text": 1}
        ).limit(limit)
        papers = list(papers)
    else:
        # Find papers without summaries
        papers = get_papers_without_summary(limit=limit)
    
    if not papers:
        print("No papers found that need summarization")
        return {"processed": 0, "successful": [], "failed": []}
    
    print(f"Found {len(papers)} papers to summarize")
    
    successful = []
    failed = []
    
    for paper in papers:
        paper_id = paper["paper_id"]
        title = paper["title"]
        text = paper["extracted_text"]
        
        print(f"Summarizing {paper_id}: {title}")
        
        try:
            # Generate summary
            summary = generate_summary(title, text, model=model)
            
            # Update MongoDB with summary
            if update_paper_with_summary(paper_id, summary):
                successful.append(paper_id)
            else:
                failed.append(paper_id)
                
        except Exception as e:
            print(f"❌ Error processing {paper_id}: {str(e)}")
            failed.append(paper_id)
    
    results = {
        "processed": len(papers),
        "successful": successful,
        "failed": failed
    }
    
    print(f"✅ Successfully summarized {len(successful)} papers")
    if failed:
        print(f"❌ Failed to summarize {len(failed)} papers")
        
    return results

if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Generate summaries for arXiv papers using LLMs")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of papers to summarize")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                       help=f"LLM model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--force", action="store_true", help="Re-summarize papers even if they already have summaries")
    
    args = parser.parse_args()
    
    print(f"Starting summarization with model: {args.model}")
    print(f"Limit: {args.limit} papers")
    if args.force:
        print("Force update: Will re-summarize papers even if they already have summaries")
    
    # Run summarization
    results = summarize_papers(
        limit=args.limit, 
        model=args.model,
        force_update=args.force
    )
    
    print("\nSummarization complete!")
    print(f"Processed: {results['processed']} papers")
    print(f"Successful: {len(results['successful'])}")
    print(f"Failed: {len(results['failed'])}")