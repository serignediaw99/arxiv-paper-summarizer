import os
import requests
import feedparser
import time
from itertools import islice

# Directory to save PDFs temporarily
DOWNLOAD_DIR = "/tmp/arxiv_pdfs"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Arxiv RSS Feed URL
RSS_FEED_URL = "https://rss.arxiv.org/rss/cs.ai"

def batch(iterable, size):
    """Helper function to create batches from an iterable"""
    iterator = iter(iterable)
    return iter(lambda: list(islice(iterator, size)), [])

def fetch_papers():
    """Fetches new AI papers from Arxiv RSS feed and downloads PDFs with arxiv-recommended rate limiting."""
    
    feed = feedparser.parse(RSS_FEED_URL)
    pdf_files = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ArxivReader/1.0; +http://example.org/bot)",
        "Accept": "application/pdf",
        "Accept-Encoding": "gzip, deflate, br"
    }

    # Process entries in bursts of 4
    for burst in batch(feed.entries, 4):
        burst_pdfs = []
        
        for entry in burst:
            paper_id = entry.id.split(":")[-1]
            title = entry.title
            pdf_url = f"https://export.arxiv.org/pdf/{paper_id}"
            pdf_path = os.path.join(DOWNLOAD_DIR, f"{paper_id}.pdf")

            try:
                with requests.Session() as session:
                    response = session.get(pdf_url, headers=headers, stream=True, timeout=30)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if 'pdf' not in content_type:
                            print(f"❌ Wrong content type for {paper_id}: {content_type}")
                            continue

                        total_size = int(response.headers.get('content-length', 0))
                        
                        with open(pdf_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        # Verify file size and PDF header
                        if total_size > 0 and os.path.getsize(pdf_path) != total_size:
                            print(f"❌ Size mismatch for {paper_id}")
                            os.remove(pdf_path)
                            continue
                            
                        with open(pdf_path, 'rb') as f:
                            pdf_header = f.read(4)
                            if pdf_header != b'%PDF':
                                print(f"❌ Invalid PDF header for {paper_id}")
                                os.remove(pdf_path)
                                continue
                        
                        burst_pdfs.append({
                            "paper_id": paper_id,
                            "pdf_path": pdf_path,
                            "title": title
                        })
                        print(f"✅ Downloaded: {title} ({paper_id}) - {os.path.getsize(pdf_path)} bytes")
                    else:
                        print(f"❌ Failed to download: {title} ({paper_id}). Status code: {response.status_code}")
                        
            except Exception as e:
                print(f"❌ Error downloading {paper_id}: {str(e)}")
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                continue

        # Add successful downloads from this burst to our results
        pdf_files.extend(burst_pdfs)
        
        # Sleep for 1 second after each burst as per arxiv guidelines
        time.sleep(1)

    return pdf_files
