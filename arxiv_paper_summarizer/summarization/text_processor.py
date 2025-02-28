import re
from typing import List, Dict, Any, Optional, Tuple

def extract_paper_sections(text: str) -> Dict[str, str]:
    """
    Extract important sections from academic paper text.
    
    Args:
        text: Full extracted text from the paper
        
    Returns:
        Dictionary mapping section names to their content
    """
    sections = {}
    
    # Search for abstract
    abstract_match = re.search(r'(?i)abstract\s*(.*?)(?:\n\n|\n[A-Z][a-z]+\s*\n)', text, re.DOTALL)
    if abstract_match:
        sections["ABSTRACT"] = abstract_match.group(1).strip()
    
    # Search for introduction
    intro_match = re.search(r'(?i)(?:introduction|background)\s*(.*?)(?:\n\n|\n[A-Z][a-z]+\s*\n)', text, re.DOTALL)
    if intro_match:
        sections["INTRODUCTION"] = intro_match.group(1).strip()
    
    # Search for methods or methodology
    methods_match = re.search(r'(?i)(?:methods|methodology|experimental setup)\s*(.*?)(?:\n\n|\n[A-Z][a-z]+\s*\n)', text, re.DOTALL)
    if methods_match:
        sections["METHODS"] = methods_match.group(1).strip()
    
    # Search for results
    results_match = re.search(r'(?i)(?:results|findings|evaluation)\s*(.*?)(?:\n\n|\n[A-Z][a-z]+\s*\n)', text, re.DOTALL)
    if results_match:
        sections["RESULTS"] = results_match.group(1).strip()
    
    # Search for discussion
    discussion_match = re.search(r'(?i)(?:discussion)\s*(.*?)(?:\n\n|\n[A-Z][a-z]+\s*\n)', text, re.DOTALL)
    if discussion_match:
        sections["DISCUSSION"] = discussion_match.group(1).strip()
    
    # Search for conclusion
    conclusion_match = re.search(r'(?i)(?:conclusion|conclusions|summary)\s*(.*?)(?:\n\n|\n[A-Z][a-z]+\s*\n|\Z)', text, re.DOTALL)
    if conclusion_match:
        sections["CONCLUSION"] = conclusion_match.group(1).strip()
    
    return sections

def prepare_text_for_llm(text: str, max_length: int = 8000) -> str:
    """
    Prepare paper text for LLM input, focusing on important sections.
    
    Args:
        text: Full extracted text from the paper
        max_length: Maximum length of the prepared text
        
    Returns:
        Processed text focusing on important sections
    """
    # Extract sections from the paper
    sections = extract_paper_sections(text)
    
    # If sections were found, use them
    if sections:
        # Prioritize key sections in this order
        priority_order = ["ABSTRACT", "INTRODUCTION", "CONCLUSION", "METHODS", "RESULTS", "DISCUSSION"]
        
        # Build structured text based on priority
        structured_text = ""
        remaining_length = max_length
        
        for section_name in priority_order:
            if section_name in sections and remaining_length > 0:
                section_content = sections[section_name]
                section_text = f"{section_name}:\n{section_content}\n\n"
                
                # Truncate section if it would exceed the remaining length
                if len(section_text) > remaining_length:
                    section_text = section_text[:remaining_length] + "...\n\n"
                
                structured_text += section_text
                remaining_length -= len(section_text)
        
        if structured_text:
            return structured_text
    
    # Fallback if no sections found or structured text is empty
    # Use the beginning and end of the paper, which often contain the most important information
    first_portion = int(max_length * 0.6)  # 60% from the beginning
    last_portion = max_length - first_portion  # 40% from the end
    
    if len(text) <= max_length:
        return text
    
    beginning = text[:first_portion]
    ending = text[-last_portion:]
    
    return f"{beginning}\n\n[...]\n\n{ending}"

def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks for processing by LLMs with limited context.
    
    Args:
        text: Text to split into chunks
        max_chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        
        # Try to find a natural breaking point (period, newline) if not at the end
        if end < len(text):
            # Look for a period or newline in the last 100 chars of the chunk
            look_back = min(100, end - start)
            break_at = text[end-look_back:end].rfind('.')
            
            if break_at != -1:
                end = end - look_back + break_at + 1
            else:
                # If no period found, try to find a newline
                break_at = text[end-look_back:end].rfind('\n')
                if break_at != -1:
                    end = end - look_back + break_at + 1
        
        # Add the chunk to our list
        chunks.append(text[start:end])
        
        # Move to next chunk with overlap
        start = end - overlap
    
    return chunks

def extract_paper_metadata(text: str) -> Dict[str, Any]:
    """
    Extract metadata from paper text such as authors, year, etc.
    
    Args:
        text: Full extracted text from the paper
        
    Returns:
        Dictionary of metadata
    """
    metadata = {}
    
    # Look for authors (typically after title and before abstract)
    authors_match = re.search(r'\n((?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s+)+)(?:\n|$)', text[:1000])
    if authors_match:
        authors = authors_match.group(1).strip()
        metadata["authors"] = authors
    
    # Look for year (typically 4 digits in the header area)
    year_match = re.search(r'(?:^|\s)(\d{4})(?:\s|$)', text[:1000])
    if year_match:
        metadata["year"] = year_match.group(1)
    
    # Look for DOI
    doi_match = re.search(r'(?i)(?:doi|DOI):\s*(10\.\d+/\S+)', text)
    if doi_match:
        metadata["doi"] = doi_match.group(1)
    
    # Look for keywords (often appears as "Keywords:" or "Index Terms:")
    keywords_match = re.search(r'(?i)(?:keywords|index terms):\s*(.*?)(?:\n\n|\.$)', text, re.DOTALL)
    if keywords_match:
        keywords = keywords_match.group(1).strip()
        metadata["keywords"] = keywords
    
    return metadata

def extract_references(text: str) -> List[str]:
    """
    Extract references from the paper text.
    
    Args:
        text: Full extracted text from the paper
        
    Returns:
        List of extracted references
    """
    # Look for references section
    references_match = re.search(r'(?i)(?:references|bibliography)\s*(.*?)(?:\Z|\n\n\n)', text, re.DOTALL)
    
    if not references_match:
        return []
    
    references_text = references_match.group(1)
    
    # Split by common reference patterns
    references = []
    
    # Try numbered references pattern first
    numbered_refs = re.findall(r'(?:^|\n)\s*\[\d+\](.*?)(?=(?:\n\s*\[\d+\]|\Z))', references_text, re.DOTALL)
    
    if numbered_refs:
        references = [ref.strip() for ref in numbered_refs]
    else:
        # Try author-year pattern
        author_year_refs = re.findall(r'(?:^|\n)([A-Z][a-z]+(?: and |, | et al\., )[A-Za-z, ]+\d{4}\..*?)(?=\n[A-Z]|\Z)', 
                                      references_text, re.DOTALL)
        if author_year_refs:
            references = [ref.strip() for ref in author_year_refs]
    
    return references

if __name__ == "__main__":
    # Sample test if run directly
    sample_text = """
    Abstract
    This paper presents a novel approach to text processing in academic papers.
    We show that our method outperforms existing approaches.
    
    Introduction
    Academic papers contain structured information that can be extracted.
    Previous work has focused on citation analysis.
    
    Methods
    We used regular expressions and natural language processing techniques.
    Our algorithm identifies section boundaries with 95% accuracy.
    
    Results
    The system achieved F1 scores of 0.89 on the test corpus.
    
    Conclusion
    We presented an effective approach for academic text processing.
    Future work will focus on improving reference extraction.
    
    References
    [1] Smith, J. (2020). Academic paper analysis. Journal of Text Mining, 5(2), 23-45.
    [2] Brown, A. et al. (2019). Section identification in papers. In Proceedings of NLP Conference.
    """
    
    # Test section extraction
    sections = extract_paper_sections(sample_text)
    print("Extracted sections:")
    for section, content in sections.items():
        print(f"{section}: {content[:50]}...")
    
    # Test text preparation
    prepared = prepare_text_for_llm(sample_text, max_length=500)
    print(f"\nPrepared text ({len(prepared)} chars):")
    print(prepared[:100] + "...")
    
    # Test chunking
    chunks = chunk_text(sample_text, max_chunk_size=200)
    print(f"\nChunks ({len(chunks)}):")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk[:30]}... ({len(chunk)} chars)")