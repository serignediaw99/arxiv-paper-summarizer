import os
from google.cloud import storage
from config.settings import GCS_BUCKET_NAME, GCP_CREDENTIALS_PATH
from fetch_pdfs import fetch_papers

# Initialize GCS client
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_CREDENTIALS_PATH
storage_client = storage.Client()

def upload_pdfs(pdf_files):
    """Uploads downloaded PDFs to Google Cloud Storage."""
    
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    uploaded_files = []

    for pdf in pdf_files:
        paper_id = pdf["paper_id"]
        pdf_path = pdf["pdf_path"]
        blob_name = f"arxiv_papers/{paper_id}.pdf"
        blob = bucket.blob(blob_name)

        # Set content type before upload
        blob.content_type = 'application/pdf'

        # Upload PDF to GCS
        blob.upload_from_filename(pdf_path)
        gcs_url = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
        uploaded_files.append({
            "paper_id": paper_id,
            "title": pdf["title"],
            "gcs_url": gcs_url
        })

        print(f"✅ Uploaded: {pdf_path} → {gcs_url}")

    return uploaded_files  # Pass to MongoDB storage
