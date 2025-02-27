import os
import io
from typing import List, Dict, Any, Optional, Union
from google.cloud import storage
import PyPDF2
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "arxiv_papers")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "arxiv_papers.papers_metadata")

# GCS Configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

# Initialize GCS client
storage_client = storage.Client()

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

print(f"Connected to MongoDB collection: {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")

def get_collection_info():
    """Print information about the MongoDB collection structure."""
    # Check collection stats
    total_count = collection.count_documents({})
    print(f"\nMongoDB Collection Information:")
    print(f"--------------------------------")
    print(f"Collection: {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")
    print(f"Total documents: {total_count}")
    
    if total_count == 0:
        print("Collection is empty. Please ensure data has been loaded.")
        return
    
    # Get a sample document to inspect its structure
    sample = collection.find_one({})
    print(f"\nSample document structure:")
    print(f"Fields: {list(sample.keys())}")
    
    # Check for common field names that might contain the GCS URL
    gcs_field_candidates = ['gcs_url', 'pdf_url', 'url', 'file_url', 'storage_url']
    found_gcs_field = None
    
    for field in gcs_field_candidates:
        if field in sample:
            found_gcs_field = field
            count = collection.count_documents({field: {"$exists": True}})
            print(f"Field '{field}' exists in {count} documents")
            print(f"Sample value: {sample[field]}")
    
    if found_gcs_field:
        print(f"\nUsing '{found_gcs_field}' as the GCS URL field")
        return found_gcs_field
    else:
        print("\nCould not identify a field containing GCS URLs.")
        print("Please check your data structure and update the code accordingly.")
        return None

def get_unprocessed_papers(limit: int = 10, url_field: str = 'gcs_url') -> List[Dict[str, Any]]:
    """
    Retrieve papers that haven't had their text extracted yet.
    
    Args:
        limit: Maximum number of papers to retrieve
        url_field: Field name containing the GCS URL
        
    Returns:
        List of paper documents from MongoDB
    """
    # First check the total number of documents
    total_count = collection.count_documents({})
    print(f"Total documents in collection: {total_count}")
    
    # Check how many have the URL field
    with_url = collection.count_documents({url_field: {"$exists": True}})
    print(f"Documents with {url_field}: {with_url}")
    
    # Check how many already have extracted_text
    with_text = collection.count_documents({"extracted_text": {"$exists": True}})
    print(f"Documents with extracted_text: {with_text}")
    
    # Get papers that have URL but no extracted_text
    query = {
        url_field: {"$exists": True},
        "extracted_text": {"$exists": False}
    }
    
    print(f"Query: {query}")
    
    papers = collection.find(
        query,
        {"paper_id": 1, "title": 1, url_field: 1}
    ).limit(limit)
    
    paper_list = list(papers)
    print(f"Found {len(paper_list)} papers that need text extraction")
    
    return paper_list

def extract_text_from_pdf(pdf_content: bytes) -> Optional[str]:
    """
    Extract text content from a PDF byte stream.
    
    Args:
        pdf_content: Binary content of the PDF file
        
    Returns:
        Extracted text as a string, or None if extraction fails
    """
    try:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        
        # Extract text from each page
        text = ""
        total_pages = len(pdf_reader.pages)
        
        for page_num in range(total_pages):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
            except Exception as e:
                print(f"Warning: Error extracting text from page {page_num}: {str(e)}")
        
        if not text.strip():
            print("Warning: No text extracted from PDF")
            return None
            
        return text
    except Exception as e:
        print(f"Error extracting text: {str(e)}")
        return None

def fetch_pdf_from_gcs(gcs_url: str) -> Optional[bytes]:
    """
    Retrieve PDF content from Google Cloud Storage.
    
    Args:
        gcs_url: GCS URL of the PDF (format: gs://bucket-name/path/to/file.pdf)
        
    Returns:
        Binary content of the PDF, or None if retrieval fails
    """
    # Extract bucket name and blob path from GCS URL
    # Format: gs://bucket-name/path/to/file.pdf
    try:
        parts = gcs_url.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        blob_path = parts[1]
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        # Download as bytes
        pdf_content = blob.download_as_bytes()
        return pdf_content
    except Exception as e:
        print(f"Error downloading from GCS: {str(e)}")
        return None

def update_paper_with_text(paper_id: str, extracted_text: str) -> bool:
    """
    Update MongoDB with the extracted text for a paper.
    
    Args:
        paper_id: ID of the paper in MongoDB
        extracted_text: Extracted text content
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        result = collection.update_one(
            {"paper_id": paper_id},
            {"$set": {"extracted_text": extracted_text}}
        )
        
        if result.modified_count == 1:
            print(f"✅ Updated MongoDB with extracted text for {paper_id}")
            return True
        else:
            print(f"⚠️ No documents matched or updated for {paper_id}")
            return False
    except Exception as e:
        print(f"❌ Error updating MongoDB: {str(e)}")
        return False

def process_pdf(paper: Dict[str, Any]) -> bool:
    """
    Process a single paper: download PDF, extract text, and update MongoDB.
    
    Args:
        paper: Paper document from MongoDB
        
    Returns:
        True if processing was successful, False otherwise
    """
    paper_id = paper["paper_id"]
    title = paper.get("title", "Untitled")
    gcs_url = paper["gcs_url"]
    
    print(f"Processing {paper_id}: {title}")
    
    # Step 1: Download PDF from GCS
    pdf_content = fetch_pdf_from_gcs(gcs_url)
    if not pdf_content:
        print(f"❌ Failed to download {paper_id} from GCS")
        return False
    
    # Step 2: Extract text from PDF
    extracted_text = extract_text_from_pdf(pdf_content)
    if not extracted_text:
        print(f"❌ Failed to extract text from {paper_id}")
        return False
    
    # Step 3: Update MongoDB with extracted text
    if not update_paper_with_text(paper_id, extracted_text):
        print(f"❌ Failed to update MongoDB for {paper_id}")
        return False
    
    return True

def process_pdfs(limit: int = 10) -> Dict[str, Union[int, List[str]]]:
    """
    Process multiple PDFs: download, extract text, and update MongoDB.
    
    Args:
        limit: Maximum number of papers to process
        
    Returns:
        Dictionary with processing results
    """
    # First check the collection structure
    url_field = get_collection_info()
    if not url_field:
        return {"processed": 0, "successful": [], "failed": []}
    
    papers = get_unprocessed_papers(limit=limit, url_field=url_field)
    
    if not papers:
        print("No unprocessed papers found.")
        return {"processed": 0, "successful": [], "failed": []}
    
    print(f"Found {len(papers)} unprocessed papers.")
    
    successful = []
    failed = []
    
    for paper in papers:
        paper_id = paper["paper_id"]
        gcs_url = paper[url_field]
        
        # Modify the paper dict to have gcs_url field for consistency
        if url_field != "gcs_url":
            paper["gcs_url"] = gcs_url
            
        if process_pdf(paper):
            successful.append(paper_id)
        else:
            failed.append(paper_id)
    
    print(f"✅ Successfully processed {len(successful)} papers")
    if failed:
        print(f"❌ Failed to process {len(failed)} papers")
    
    return {
        "processed": len(papers),
        "successful": successful,
        "failed": failed
    }

if __name__ == "__main__":
    import argparse
    
    # Create command line parser
    parser = argparse.ArgumentParser(description="Process PDFs from Google Cloud Storage and extract text")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of PDFs to process")
    args = parser.parse_args()
    
    print(f"Starting PDF processing with limit: {args.limit}")
    results = process_pdfs(limit=args.limit)
    print(f"Results: {results}")