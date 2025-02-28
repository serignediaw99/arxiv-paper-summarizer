import os
import sys
import argparse
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

# Import processing modules
from arxiv_paper_summarizer.summarization.pdf_processor import process_pdfs
from arxiv_paper_summarizer.summarization.summarizer import summarize_papers

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Process and summarize arXiv papers")
    parser.add_argument("--process", action="store_true", help="Process PDFs to extract text")
    parser.add_argument("--summarize", action="store_true", help="Generate summaries for processed papers")
    parser.add_argument("--pdf-limit", type=int, default=10, 
                        help="Maximum number of PDFs to process for text extraction")
    parser.add_argument("--summary-limit", type=int, default=5, 
                        help="Maximum number of papers to process for summarization")
    parser.add_argument("--model", type=str, 
                        help="LLM model to use (overrides settings.py)")
    parser.add_argument("--force-summarize", action="store_true",
                        help="Re-summarize papers even if they already have summaries")
    return parser.parse_args()

def main():
    """Main function to run the paper processing pipeline."""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Default to running all steps if none are specified
    if not args.process and not args.summarize:
        args.process = True
        args.summarize = True
    
    # Get model from env or CLI
    model = args.model or os.getenv("OLLAMA_MODEL", "mistral")
    
    results = {}
    
    # Process PDFs (extract text)
    if args.process:
        print(f"\n--- Step 1: Processing PDFs to extract text (limit: {args.pdf_limit}) ---")
        start_time = time.time()
        
        pdf_results = process_pdfs(limit=args.pdf_limit)
        
        elapsed_time = time.time() - start_time
        results["pdf_processing"] = pdf_results
        results["pdf_processing"]["time"] = f"{elapsed_time:.2f} seconds"
        
        print(f"✅ PDF processing complete in {elapsed_time:.2f} seconds")
        print(f"   Processed: {pdf_results['processed']} PDFs")
        print(f"   Successful: {len(pdf_results['successful'])}")
        print(f"   Failed: {len(pdf_results['failed'])}")
        print("-" * 70)
    
    # Generate summaries
    if args.summarize:
        print(f"\n--- Step 2: Generating summaries with model: {model} (limit: {args.summary_limit}) ---")
        
        start_time = time.time()
        
        summary_results = summarize_papers(
            limit=args.summary_limit,
            model=model,
            force_update=args.force_summarize
        )
        
        elapsed_time = time.time() - start_time
        results["summarization"] = summary_results
        results["summarization"]["time"] = f"{elapsed_time:.2f} seconds"
        
        print(f"✅ Summarization complete in {elapsed_time:.2f} seconds")
        print(f"   Processed: {summary_results['processed']} papers")
        print(f"   Successful: {len(summary_results['successful'])}")
        print(f"   Failed: {len(summary_results['failed'])}")
        print("-" * 70)
    
    print("\nPipeline execution complete!")
    
    return results

if __name__ == "__main__":
    main()