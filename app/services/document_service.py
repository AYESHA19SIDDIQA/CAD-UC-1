"""
Main document generation service
"""
from typing import Dict, List
from app.extraction.pdf_parser import PDFParser
from app.extraction.llm_extractor import LLMExtractor
from app.services.rule_engine import RuleEngine
from app.utils.docx_generator import DocxGenerator
from app.schemas.sanction_schema import SanctionData

class DocumentService:
    """Orchestrate the document generation process"""
    
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.llm_extractor = LLMExtractor()
        self.rule_engine = RuleEngine()
        self.docx_generator = DocxGenerator()
    
    async def process_sanction_letter(self, pdf_content: bytes) -> Dict:
        """
        Process sanction letter and generate required documents
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary with processing results
        """
        # Step 1: Extract text from PDF
        text = self.pdf_parser.extract_text(pdf_content)
        
        # Step 2: Use LLM to extract structured data
        sanction_data = self.llm_extractor.extract_sanction_data(text)
        
        # Step 3: Validate data against business rules
        validation_result = self.rule_engine.validate_sanction_data(sanction_data)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": validation_result.get("reason", "Validation failed")
            }
        
        # Step 4: Determine required documents
        required_docs = self.rule_engine.determine_required_documents(sanction_data)
        
        # Step 5: Generate documents
        generated_files = []
        for doc_type in required_docs:
            file_path = self.docx_generator.generate_document(doc_type, sanction_data)
            generated_files.append(file_path)
        
        return {
            "success": True,
            "sanction_data": sanction_data.model_dump(),
            "generated_files": generated_files
        }
