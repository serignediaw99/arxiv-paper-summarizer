"""
DAG for fetching ArXiv papers and storing them in Google Cloud Storage and MongoDB.
Optimized for Cloud Composer environment.
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.models import Variable

import os
import requests
import feedparser
import time
from itertools import islice
from datetime import datetime, timedelta

# Define default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 2, 18),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def batch(iterable, size):
    """Helper function to create batches from an iterable"""
    iterator = iter(iterable)
    return iter(lambda: list(islice(iterator, size)), [])

def fetch_papers(**context):
    """Fetches new AI papers from ArXiv RSS feed with rate limiting."""
    RSS_FEED_URL = Variable.get("ARXIV_RSS_FEED")
    
    # Use Cloud Composer's temp directory
    DOWNLOAD_DIR = '/home/airflow/gcs/data/arxiv_pdfs'
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    feed = feedparser.parse(RSS_FEED_URL)
    pdf_files = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ArxivReader/1.0; +https://cloud.google.com)",
        "Accept": "application/pdf"
    }

    for burst in batch(feed.entries, 4):
        burst_pdfs = []
        
        for entry in burst:
            paper_id = entry.id.split(":")[-1]
            pdf_path = os.path.join(DOWNLOAD_DIR, f"{paper_id}.pdf")
            
            try:
                response = requests.get(
                    f"https://export.arxiv.org/pdf/{paper_id}",
                    headers=headers,
                    stream=True,
                    timeout=30
                )
                
                if response.status_code == 200:
                    with open(pdf_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    burst_pdfs.append({
                        "paper_id": paper_id,
                        "pdf_path": pdf_path,
                        "title": entry.title
                    })
                    print(f"✅ Downloaded: {entry.title} ({paper_id})")
                    
            except Exception as e:
                print(f"❌ Error downloading {paper_id}: {str(e)}")
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                continue

        pdf_files.extend(burst_pdfs)
        time.sleep(1)  # Rate limiting

    context['task_instance'].xcom_push(key='pdf_files', value=pdf_files)
    return pdf_files

def upload_to_gcs(**context):
    """Uploads PDFs to Google Cloud Storage using GCSHook."""
    pdf_files = context['task_instance'].xcom_pull(task_ids='fetch_papers', key='pdf_files')
    bucket_name = Variable.get("GCS_BUCKET_NAME")
    
    gcs_hook = GCSHook()
    uploaded_files = []

    for pdf in pdf_files:
        paper_id = pdf["paper_id"]
        pdf_path = pdf["pdf_path"]
        blob_name = f"arxiv_papers/{paper_id}.pdf"

        try:
            gcs_hook.upload(
                bucket_name=bucket_name,
                object_name=blob_name,
                filename=pdf_path,
                mime_type='application/pdf'
            )
            
            gcs_url = f"gs://{bucket_name}/{blob_name}"
            uploaded_files.append({
                "paper_id": paper_id,
                "title": pdf["title"],
                "gcs_url": gcs_url
            })
            
            # Clean up local file
            os.remove(pdf_path)
            print(f"✅ Uploaded: {pdf_path} → {gcs_url}")
            
        except Exception as e:
            print(f"❌ Error uploading {paper_id}: {str(e)}")

    context['task_instance'].xcom_push(key='uploaded_files', value=uploaded_files)
    return uploaded_files

def store_in_mongodb(**context):
    """Stores paper metadata in MongoDB using MongoHook."""
    uploaded_files = context['task_instance'].xcom_pull(task_ids='upload_to_gcs', key='uploaded_files')
    
    mongo_hook = MongoHook(conn_id='mongo_default')
    db_name = Variable.get("MONGO_DB_NAME")
    collection_name = Variable.get("MONGO_COLLECTION_NAME")

    try:
        for paper in uploaded_files:
            mongo_hook.update_one(
                mongo_collection=f"{db_name}.{collection_name}",
                filter_doc={"paper_id": paper["paper_id"]},
                update_doc={"$set": paper},
                upsert=True
            )
            print(f"✅ Stored in MongoDB: {paper['title']} ({paper['paper_id']})")
    except Exception as e:
        print(f"❌ Error storing in MongoDB: {str(e)}")
        raise

    return True

# Create the DAG
dag = DAG(
    'arxiv_paper_tracking',
    default_args=default_args,
    description='Fetch ArXiv papers and store in GCS and MongoDB',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['arxiv', 'papers', 'ai']
)

# Define tasks
fetch_papers_task = PythonOperator(
    task_id='fetch_papers',
    python_callable=fetch_papers,
    provide_context=True,
    dag=dag,
)

upload_to_gcs_task = PythonOperator(
    task_id='upload_to_gcs',
    python_callable=upload_to_gcs,
    provide_context=True,
    dag=dag,
)

store_in_mongodb_task = PythonOperator(
    task_id='store_in_mongodb',
    python_callable=store_in_mongodb,
    provide_context=True,
    dag=dag,
)

# Set task dependencies
fetch_papers_task >> upload_to_gcs_task >> store_in_mongodb_task