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
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "6.0"))

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

def get_papers_with_summaries(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve papers that have summaries, for relevance analysis.
    
    Args:
        limit: Maximum number of papers to retrieve
        
    Returns:
        List of paper documents from MongoDB
    """
    papers = collection.find(
        {
            "summary": {"$exists": True}
        },
        {
            "paper_id": 1, 
            "title": 1, 
            "summary": 1
        }
    ).limit(limit)
    
    return list(papers)

def analyze_relevance(
    title: str, 
    summary: str,
    topics: List[str], 
    model: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Use LLM to determine relevance of a paper to specified topics.
    
    Args:
        title: The paper title
        summary: The paper summary
        topics: List of research topics to check relevance against
        model: Ollama model to use
    
    Returns:
        Dictionary with relevance score and explanation
    """
    # Format topics for prompt
    topics_str = ", ".join(topics)
    
    prompt = f"""
    You are tasked with evaluating the relevance of a research paper to specific topics.

    PAPER TITLE: {title}

    PAPER SUMMARY:
    {summary}

    RESEARCH TOPICS OF INTEREST: {topics_str}

    Evaluate how relevant this paper is to the specified research topics on a scale of 0-10.
    Provide a brief explanation (2-3 sentences) for your rating.

    Format your response as:
    RELEVANCE_SCORE: [score 0-10]
    EXPLANATION: [your brief explanation]
    """
    
    # Query Ollama
    response = query_ollama(prompt, model=model, max_tokens=300, temperature=0.0)
    
    # Extract score and explanation using regex
    score_match = re.search(r'RELEVANCE_SCORE:\s*(\d+(?:\.\d+)?)', response)
    explanation_match = re.search(r'EXPLANATION:\s*(.*?)(?:\n|$)', response, re.DOTALL)
    
    if score_match and explanation_match:
        try:
            score = float(score_match.group(1))
            explanation = explanation_match.group(1).strip()
            
            return {
                "score": score,
                "explanation": explanation,
                "is_relevant": score >= RELEVANCE_THRESHOLD
            }
        except Exception as e:
            print(f"Error parsing relevance score: {str(e)}")
    
    # Fallback if parsing fails
    # Simple keyword-based matching
    keyword_score = 0
    for topic in topics:
        if topic.lower() in title.lower() or topic.lower() in summary.lower():
            keyword_score += 2
            
    backup_score = min(10, keyword_score)
    
    return {
        "score": backup_score,
        "explanation": "Score based on keyword matching (fallback method).",
        "is_relevant": backup_score >= RELEVANCE_THRESHOLD
    }

def find_relevant_papers(
    topics: List[str],
    limit: int = 10,
    model: str = DEFAULT_MODEL
) -> List[Dict[str, Any]]:
    """
    Find papers relevant to the specified topics by analyzing them on-demand.
    
    Args:
        topics: List of research topics to check relevance for
        limit: Maximum number of papers to retrieve and analyze
        model: LLM model to use
        
    Returns:
        List of papers with relevance information, sorted by relevance
    """
    # Get papers with summaries
    papers = get_papers_with_summaries(limit=limit)
    
    if not papers:
        print("No papers with summaries found in the database.")
        return []
    
    print(f"Analyzing relevance of {len(papers)} papers to topics: {topics}")
    
    # Analyze relevance for each paper
    results = []
    for paper in papers:
        paper_id = paper["paper_id"]
        title = paper["title"]
        summary = paper["summary"]
        
        print(f"Analyzing {paper_id}: {title}")
        
        try:
            # Analyze relevance
            relevance = analyze_relevance(title, summary, topics, model=model)
            
            # Add relevance information to the paper
            paper["relevance"] = relevance
            
            # Add to results if relevant
            if relevance["is_relevant"]:
                print(f"✅ Relevant (Score: {relevance['score']}/10)")
                results.append(paper)
            else:
                print(f"❌ Not relevant (Score: {relevance['score']}/10)")
                
        except Exception as e:
            print(f"Error analyzing {paper_id}: {str(e)}")
    
    # Sort by relevance score (descending)
    results.sort(key=lambda x: x["relevance"]["score"], reverse=True)
    
    print(f"Found {len(results)} relevant papers out of {len(papers)} analyzed.")
    
    return results

if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Analyze paper relevance to research topics")
    parser.add_argument("--topics", type=str, required=True,
                       help="Comma-separated list of topics to check relevance against")
    parser.add_argument("--limit", type=int, default=10, 
                       help="Maximum number of papers to analyze")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                       help=f"LLM model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--threshold", type=float, default=RELEVANCE_THRESHOLD,
                       help=f"Relevance threshold score (default: {RELEVANCE_THRESHOLD})")
    
    args = parser.parse_args()
    
    # Update threshold if provided
    if args.threshold != RELEVANCE_THRESHOLD:
        RELEVANCE_THRESHOLD = args.threshold
    
    # Parse topics into a list
    topic_list = [topic.strip() for topic in args.topics.split(",")]
    
    # Run relevance analysis
    print(f"Finding papers relevant to topics: {topic_list}")
    print(f"Using model: {args.model}")
    print(f"Relevance threshold: {RELEVANCE_THRESHOLD}")
    
    relevant_papers = find_relevant_papers(
        topics=topic_list,
        limit=args.limit,
        model=args.model
    )
    
    print("\nRelevant Papers:")
    print("-" * 50)
    
    for i, paper in enumerate(relevant_papers, 1):
        relevance = paper["relevance"]
        
        print(f"\n{i}. {paper['title']} (ID: {paper['paper_id']})")
        print(f"   Relevance: {relevance['score']}/10")
        print(f"   Explanation: {relevance['explanation']}")
        
        # Print a snippet of the summary
        summary = paper.get("summary", "No summary available")
        if len(summary) > 150:
            print(f"   Summary: {summary[:150]}...")
        else:
            print(f"   Summary: {summary}")