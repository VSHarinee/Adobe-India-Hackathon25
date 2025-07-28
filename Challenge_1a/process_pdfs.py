import os
import json
import fitz  # PyMuPDF
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional

class PDFOutlineExtractor:
    """Optimized PDF outline extractor using font size analysis."""
    
    def __init__(self, min_heading_length: int = 4, max_heading_levels: int = 3):
        self.min_heading_length = min_heading_length
        self.max_heading_levels = max_heading_levels
    
    def _analyze_font_sizes(self, doc: fitz.Document) -> Dict[float, str]:
        """Analyze font sizes across all pages to determine heading levels."""
        font_counter = Counter()
        
        for page in doc:
            # Use get_text("dict") once per page for efficiency
            text_dict = page.get_text("dict")
            for block in text_dict["blocks"]:
                if block["type"] == 0:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if len(span["text"].strip()) >= self.min_heading_length:
                                font_counter[span["size"]] += 1
        
        # Get top font sizes by frequency (likely headings appear multiple times)
        top_sizes = [size for size, _ in font_counter.most_common()]
        # Sort by size descending for hierarchy
        top_sizes = sorted(set(top_sizes), reverse=True)[:self.max_heading_levels]
        
        # Map sizes to heading levels
        return {size: f"H{i+1}" for i, size in enumerate(top_sizes)}
    
    def _extract_headings_from_page(self, page: fitz.Page, page_num: int, 
                                  size_to_level: Dict[float, str]) -> List[Dict]:
        """Extract headings from a single page."""
        headings = []
        processed_texts = set()  # Avoid duplicate headings on same page
        
        text_dict = page.get_text("dict")
        for block in text_dict["blocks"]:
            if block["type"] == 0:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        
                        # Filter criteria
                        if (len(text) < self.min_heading_length or 
                            text in processed_texts or
                            span["size"] not in size_to_level):
                            continue
                        
                        # Additional heuristics for better heading detection
                        if self._is_likely_heading(text):
                            headings.append({
                                "level": size_to_level[span["size"]],
                                "text": text,
                                "page": page_num,
                                "font_size": span["size"]
                            })
                            processed_texts.add(text)
        
        return headings
    
    def _is_likely_heading(self, text: str) -> bool:
        """Apply heuristics to determine if text is likely a heading."""
        # Skip if mostly numbers or special characters
        if sum(c.isalnum() for c in text) / len(text) < 0.5:
            return False
        
        # Skip very long texts (likely paragraphs)
        if len(text) > 200:
            return False
        
        # Skip texts that end with common sentence endings
        if text.endswith(('.', '!', '?', ';')):
            return False
        
        return True
    
    def extract_outline(self, pdf_path: Path) -> Optional[Dict]:
        """Extract outline from PDF file."""
        try:
            with fitz.open(pdf_path) as doc:
                if len(doc) == 0:
                    return None
                
                # Analyze font sizes
                size_to_level = self._analyze_font_sizes(doc)
                if not size_to_level:
                    return None
                
                # Extract headings
                all_headings = []
                for page_num, page in enumerate(doc, start=1):
                    headings = self._extract_headings_from_page(page, page_num, size_to_level)
                    all_headings.extend(headings)
                
                # Remove font_size from final output
                for heading in all_headings:
                    heading.pop('font_size', None)
                
                return {
                    "title": pdf_path.stem,
                    "outline": all_headings,
                    "total_pages": len(doc),
                    "headings_found": len(all_headings)
                }
        
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            return None

def process_pdfs(input_dir: str = "Challenge_1a/app/input/",
                output_dir: str = "Challenge_1a/app/output/") -> None:
    """Process all PDF files in input directory."""
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Validate input directory
    if not input_path.exists():
        print(f"Input directory not found: {input_path}")
        return
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get PDF files
    pdf_files = list(input_path.glob("*.pdf"))
    if not pdf_files:
        print(f"📄 No PDF files found in {input_path}")
        return
    
    print(f"🔍 Found {len(pdf_files)} PDF files to process...")
    
    # Initialize extractor
    extractor = PDFOutlineExtractor()
    
    # Process files
    successful = 0
    failed = 0
    
    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}...", end=' ')
        
        outline_data = extractor.extract_outline(pdf_file)
        
        if outline_data:
            output_file = output_path / f"{pdf_file.stem}.json"
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(outline_data, f, indent=2, ensure_ascii=False)
                print(f"Success ({outline_data['headings_found']} headings)")
                successful += 1
            except Exception as e:
                print(f"Failed to write output: {e}")
                failed += 1
        else:
            print("Failed to extract outline")
            failed += 1
    
    print(f"\n Processing complete:")
    print(f"    Successful: {successful}")
    print(f"    Failed: {failed}")
    print(f"    Output directory: {output_path}")

if __name__ == "__main__":
    print(" Starting PDF outline extraction...")
    process_pdfs()
    print(" Finished processing.")