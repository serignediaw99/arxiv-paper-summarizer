# ArXiv Paper Summarizer

This project implements an automated pipeline for fetching, storing, processing, and summarizing academic papers from ArXiv's AI category. The system processes PDFs into summaries and provides on-demand relevance analysis for specific research topics.

## Architecture

The system consists of three main components:

1. **Paper Fetching**: Daily fetching of new AI papers from ArXiv's RSS feed
2. **Storage**: Papers are stored in Google Cloud Storage with metadata in MongoDB Atlas
3. **Text Extraction**: PDFs are processed to extract their text content
4. **Summarization**: Papers are summarized using LLMs (Ollama/Mistral)
5. **Relevance Analysis**: On-demand analysis of paper relevance to specific research topics

## Cloud Infrastructure

- **Cloud Composer**: Manages the Airflow DAG workflow
- **Google Cloud Storage**: Stores PDF files (`arxiv-pdf-storage` bucket)
- **MongoDB Atlas**: Stores paper metadata
- **Local Ollama**: Runs LLMs for summarization and relevance analysis.

## DAG Structure

The DAG (`arxiv_paper_dag.py`) runs daily and consists of three tasks:

1. `fetch_pdfs`: Downloads new papers from ArXiv's RSS feed
2. `upload_to_gcs`: Uploads PDFs to Google Cloud Storage
3. `store_in_mongodb`: Stores metadata in MongoDB Atlas

## Pipeline Structure

The pipeline consists of multiple steps:
1. `fetch_pdfs`: Downloads new papers from ArXiv's RSS feed
2. `upload_to_gcs`: Uploads PDFs to Google Cloud Storage
3. `store_in_mongodb`: Stores metadata in MongoDB Atlas
4. `pdf_processor`: Extracts text from PDFs and stores it in MongoDB
5. `summarizer`: Generates summaries of papers using LLMs and stores them in MongoDB
6. `relevance_analysis`: Generates relevance scores for stored papers using topic key words

## Setup Requirements

### Google Cloud Platform
- GCP project with Cloud Composer enabled
- Service account with appropriate permissions
- GCS bucket for PDF storage

### MongoDB Atlas
- MongoDB Atlas cluster
- Database user credentials
- Network access configured

### Local LLM Setup
- Ollama installed locally
- Mistral model pulled: ollama pull mistral

### Environment Variables
The following Airflow variables need to be set in Cloud Composer:
- `GCS_BUCKET_NAME`: Your GCS bucket name
- `MONGO_DB_NAME`: MongoDB database name
- `MONGO_COLLECTION_NAME`: MongoDB collection name
- `ARXIV_RSS_FEED`: ArXiv RSS feed URL

## Project Structure

```
arxiv-paper-summarizer/
└── arxiv_paper_summarizer/
    ├── composer/
    │   └── dags/
    │       └── arxiv_paper_dag.py
    ├── config/
    │   ├── __init__.py
    │   └── settings.py
    ├── summarization/         # Future feature
    ├── fetch_pdfs.py
    ├── mongo_handler.py
    └── upload_to_gcs.py
```

## Deployment

The DAG is deployed on Cloud Composer. To deploy updates:

1. Make changes to the DAG file
2. Upload to Cloud Composer's DAGs folder (either via console or gcloud command)
3. Cloud Composer will automatically detect and apply changes

## MongoDB Data Structure

Papers are stored in MongoDB with the following structure:
- Database: `arxiv_papers`
- Collection: `papers_metadata`
- Document structure:
  ```json
  {
    "paper_id": "unique_arxiv_id",
    "title": "paper_title",
    "gcs_url": "gs://bucket-name/arxiv_papers/paper_id.pdf",
    "extracted_text": "full paper text content",
    "summary": "structured summary of the paper"
  }
  ```

## Access and Permissions

To request access to:
- Cloud Composer environment: Contact GCP project admin
- MongoDB Atlas: Contact database admin
- GCS bucket: Contact GCP project admin

## Local Development

### Prerequisites
- Python 3.11+
- Virtual environment manager
- Google Cloud SDK
- Access to MongoDB Atlas cluster
- Access to GCP project
- Ollama installed locally

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/serignediaw99/arxiv-paper-summarizer.git
cd arxiv-paper-summarizer
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```
# Google Cloud Storage Configuration
GCS_BUCKET_NAME=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json

# MongoDB Configuration
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net
MONGO_DB_NAME=arxiv_papers
MONGO_COLLECTION_NAME=arxiv_papers.papers_metadata

# Arxiv Configuration
ARXIV_RSS_FEED=https://rss.arxiv.org/rss/cs.ai

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
RELEVANCE_THRESHOLD=6.0
```

### Usage

#### Running the Pipeline

1. Start Ollama in a separate terminal:
   ```bash
   ollama serve
   ```

2. Run the full pipeline:
   ```bash
   python -m arxiv_paper_summarizer.paper_pipeline
   ```

3. Process specific steps:
   ```bash
   # Only process PDFs
   python -m arxiv_paper_summarizer.paper_pipeline --process --pdf-limit 20

   # Only generate summaries
   python -m arxiv_paper_summarizer.paper_pipeline --summarize --summary-limit 10
   
   # Re-summarize papers
   python -m arxiv_paper_summarizer.paper_pipeline --summarize --force-summarize
   ```

#### Finding Relevant Papers

To find papers relevant to specific research topics:

```bash
python -m arxiv_paper_summarizer.summarization.relevance_analyzer --topics "quantum computing, machine learning" --limit 20
```

This analyzes papers on-demand and returns those relevant to the specified topics, without storing relevance scores in the database.

### Running Airflow Locally

1. Set Airflow home:
```bash
export AIRFLOW_HOME=~/airflow
```

2. Initialize Airflow database:
```bash
airflow db init
```

3. Create Airflow admin user:
```bash
airflow users create \
    --username admin \
    --firstname YOUR_FIRST_NAME \
    --lastname YOUR_LAST_NAME \
    --role Admin \
    --email your@email.com \
    --password your_password
```

4. Start Airflow webserver (in one terminal):
```bash
airflow webserver --port 8080
```

5. Start Airflow scheduler (in another terminal):
```bash
airflow scheduler
```

6. Access Airflow UI at http://localhost:8080

### Setting up Local Variables and Connections

In the Airflow UI:

1. Add Variables (Admin -> Variables):
   - GCS_BUCKET_NAME
   - MONGO_DB_NAME
   - MONGO_COLLECTION_NAME
   - ARXIV_RSS_FEED

2. Add Connections (Admin -> Connections):
   - MongoDB Connection:
     ```
     Conn Id: mongo_default
     Conn Type: MongoDB
     Extra: {"uri": "your_mongodb_atlas_uri"}
     ```
   - Google Cloud Connection:
     ```
     Conn Id: google_cloud_default
     Conn Type: Google Cloud
     Keyfile Path: path/to/your/service-account.json
     ```

### Testing

1. Ensure your DAG appears in the Airflow UI
2. Toggle the DAG on
3. Trigger a test run
4. Monitor logs in the Airflow UI

## Notes

- This project can be run with the Airflow capabilities, or by using the pdfs already stored in the cloud.
- The DAG runs daily to fetch new papers
- PDFs are temporarily stored in Cloud Composer's managed bucket before being moved to the final GCS location
- MongoDB connection requires specific configuration in Cloud Composer
