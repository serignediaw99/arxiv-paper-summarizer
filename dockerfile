# Use official Python image
FROM python:3.10

# Set working directory inside the container
WORKDIR /app

# Copy the entire project into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r /app/arxiv_paper_summarizer/api/requirements.txt

# Set PYTHONPATH so Python recognizes `arxiv_paper_summarizer`
ENV PYTHONPATH="/app:/app/arxiv_paper_summarizer"

# Expose API port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "arxiv_paper_summarizer.api.main:app", "--host", "0.0.0.0", "--port", "8000"]