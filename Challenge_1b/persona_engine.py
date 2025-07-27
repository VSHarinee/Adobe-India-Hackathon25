import os
import json
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Tuple, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFDocumentProcessor:
    """Process PDF documents to extract relevant sections based on persona and task."""
    
    def __init__(self, max_sections: int = 5, max_text_length: int = 500):
        self.max_sections = max_sections
        self.max_text_length = max_text_length
    
    def calculate_relevance_score(self, text: str, keywords: List[str]) -> int:
        """
        Calculate relevance score based on keyword frequency in text.
        
        Args:
            text: Text content to score
            keywords: List of keywords to search for
            
        Returns:
            Integer score representing relevance
        """
        text_lower = text.lower()
        return sum(1 for keyword in keywords if keyword in text_lower)
    
    def extract_page_text(self, page) -> str:
        """
        Extract clean text from a PDF page.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            Extracted text as string
        """
        text_blocks = []
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block["type"] == 0:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_blocks.append(span["text"])
        
        return " ".join(text_blocks)
    
    def process_pdf_document(self, pdf_path: Path, keywords: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """
        Process a single PDF document to extract relevant sections.
        
        Args:
            pdf_path: Path to PDF file
            keywords: List of keywords for relevance scoring
            
        Returns:
            Tuple of (relevant_sections, detailed_subsections)
        """
        if not pdf_path.exists():
            logger.warning(f"PDF file not found: {pdf_path}")
            return [], []
        
        try:
            doc = fitz.open(pdf_path)
            relevant_sections = []
            detailed_subsections = []
            filename = pdf_path.name
            
            for page_num, page in enumerate(doc, start=1):
                page_text = self.extract_page_text(page)
                
                if not page_text.strip():
                    continue
                
                relevance_score = self.calculate_relevance_score(page_text, keywords)
                
                if relevance_score > 1:
                    relevant_sections.append({
                        "document": filename,
                        "section_title": f"Page {page_num}",
                        "importance_rank": relevance_score,
                        "page_number": page_num
                    })
                    
                    detailed_subsections.append({
                        "document": filename,
                        "refined_text": page_text.strip()[:self.max_text_length],
                        "page_number": page_num
                    })
            
            doc.close()
            return relevant_sections, detailed_subsections
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return [], []
    
    def load_configuration(self, config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to configuration JSON file
            
        Returns:
            Dictionary containing configuration data
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
    
    def save_results(self, output_path: Path, results: Dict[str, Any]) -> None:
        """
        Save processing results to JSON file.
        
        Args:
            output_path: Path for output file
            results: Results dictionary to save
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving results to {output_path}: {str(e)}")
            raise
    
    def discover_collection_paths(self, base_directory: Path) -> List[Path]:
        """
        Discover available collection directories.
        
        Args:
            base_directory: Base directory to search for collections
            
        Returns:
            List of valid collection paths
        """
        collections = ["Collection 1", "Collection 2", "Collection 3"]
        valid_paths = []
        
        logger.info(f"Searching for collections in: {base_directory.absolute()}")
        
        for collection_name in collections:
            collection_path = base_directory / collection_name
            config_file = collection_path / "challenge1b_input.json"
            
            if collection_path.exists():
                if config_file.exists():
                    valid_paths.append(collection_path)
                    logger.info(f"Found valid collection: {collection_path}")
                else:
                    logger.warning(f"Collection exists but missing config file: {config_file}")
            else:
                logger.warning(f"Collection directory not found: {collection_path}")
        
        return valid_paths

    def process_document_collection(self, collection_path: Path) -> None:
        """
        Process a collection of PDF documents.
        
        Args:
            collection_path: Path object pointing to the collection folder
        """
        logger.info(f"Processing collection: {collection_path.name}")
        
        # Setup paths
        config_file = collection_path / "challenge1b_input.json"
        output_file = collection_path / "challenge1b_output.json"
        pdf_directory = collection_path / "PDFs"
        
        try:
            # Load configuration
            config_data = self.load_configuration(config_file)
            
            # Extract configuration parameters
            persona_role = config_data["persona"]["role"]
            task_description = config_data["job_to_be_done"]["task"]
            document_list = config_data["documents"]
            
            # Generate keywords for relevance scoring
            combined_keywords = f"{persona_role} {task_description}".lower().split()
            
            # Process all documents
            all_relevant_sections = []
            all_detailed_subsections = []
            processed_documents = []
            
            for doc_info in document_list:
                pdf_path = pdf_directory / doc_info["filename"]
                processed_documents.append(doc_info["filename"])
                
                sections, subsections = self.process_pdf_document(pdf_path, combined_keywords)
                all_relevant_sections.extend(sections)
                all_detailed_subsections.extend(subsections)
            
            # Sort by importance and limit results
            top_sections = sorted(
                all_relevant_sections, 
                key=lambda x: x["importance_rank"], 
                reverse=True
            )[:self.max_sections]
            
            # Prepare output
            processing_results = {
                "metadata": {
                    "input_documents": processed_documents,
                    "persona": persona_role,
                    "job_to_be_done": task_description
                },
                "extracted_sections": top_sections,
                "subsection_analysis": all_detailed_subsections
            }
            
            # Save results
            self.save_results(output_file, processing_results)
            
        except Exception as e:
            logger.error(f"Error processing collection {collection_path.name}: {str(e)}")
            raise

def main():
    """Main function to process all document collections."""
    processor = PDFDocumentProcessor()
    
    # Get the directory where the script is located
    script_dir = Path(__file__).parent
    
    # Try different possible locations for collections
    possible_base_paths = [
        script_dir / "Challenge_1b",  # If collections are in Challenge_1b subdirectory
        script_dir,                   # If collections are in the same directory as script
        Path.cwd(),                   # Current working directory
    ]
    
    collection_paths = []
    
    for base_path in possible_base_paths:
        if base_path.exists():
            found_paths = processor.discover_collection_paths(base_path)
            if found_paths:
                collection_paths = found_paths
                break
    
    if not collection_paths:
        logger.error("No valid collections found in any of the expected locations:")
        for path in possible_base_paths:
            logger.error(f"  - {path.absolute()}")
        logger.error("Please ensure Collection 1, 2, and 3 directories exist with challenge1b_input.json files")
        return
    
    # Process all found collections
    successful_collections = 0
    for collection_path in collection_paths:
        try:
            processor.process_document_collection(collection_path)
            successful_collections += 1
        except Exception as e:
            logger.error(f"Failed to process {collection_path.name}: {str(e)}")
            continue
    
    logger.info(f"Processing completed. Successfully processed {successful_collections}/{len(collection_paths)} collections.")

if __name__ == "__main__":
    main()