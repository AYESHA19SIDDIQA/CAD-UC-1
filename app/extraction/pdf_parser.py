"""
PDF parsing utilities
"""
import pymupdf  # PyMuPDF
from typing import Dict, List

class PDFParser:
    """Extract text and metadata from PDF files"""
    
    def __init__(self):
        pass
    
    def extract_text(self, pdf_content: bytes) -> str:
        """
        Extract all text from a PDF file
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Extracted text as string
        """
        doc = pymupdf.open(stream=pdf_content, filetype="pdf")
        text = ""
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text += page.get_text()
        
        doc.close()
        return text
    
    def extract_structured_data(self, pdf_content: bytes) -> Dict:
        """
        Extract structured data from PDF
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary containing structured data
        """
        text = self.extract_text(pdf_content)
        
        return {
            "text": text,
            "page_count": len(pdf_content)
        }
