"""
DOCX document generation utilities
"""
import os
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches
from typing import Dict
from app.schemas.sanction_schema import SanctionData

class DocxGenerator:
    """Generate DOCX documents from templates"""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        self.output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "output")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_document(self, doc_type: str, sanction_data: SanctionData) -> str:
        """
        Generate a document from template
        
        Args:
            doc_type: Type of document to generate
            sanction_data: Data to populate in the document
            
        Returns:
            Path to generated file
        """
        template_path = os.path.join(self.template_dir, f"{doc_type}.docx")
        
        if os.path.exists(template_path):
            doc = Document(template_path)
            self._replace_placeholders(doc, sanction_data)
        else:
            # Create document from scratch if template doesn't exist
            doc = self._create_document_from_scratch(doc_type, sanction_data)
        
        # Save generated document
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{doc_type}_{sanction_data.customer_name}_{timestamp}.docx"
        output_path = os.path.join(self.output_dir, output_filename)
        
        doc.save(output_path)
        return output_path
    
    def _replace_placeholders(self, doc: Document, data: SanctionData):
        """Replace placeholders in document with actual data"""
        replacements = {
            "{{CUSTOMER_NAME}}": data.customer_name,
            "{{FACILITY_TYPE}}": data.facility_type,
            "{{FACILITY_AMOUNT}}": f"{data.currency} {data.facility_amount:,.2f}",
            "{{TENOR}}": f"{data.tenor} months",
            "{{PROFIT_RATE}}": f"{data.profit_rate}%",
            "{{PURPOSE}}": data.purpose,
            "{{SECURITY}}": data.security or "N/A",
            "{{DATE}}": datetime.now().strftime("%B %d, %Y")
        }
        
        for paragraph in doc.paragraphs:
            for key, value in replacements.items():
                if key in paragraph.text:
                    paragraph.text = paragraph.text.replace(key, str(value))
        
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, value in replacements.items():
                        if key in cell.text:
                            cell.text = cell.text.replace(key, str(value))
    
    def _create_document_from_scratch(self, doc_type: str, data: SanctionData) -> Document:
        """Create a basic document if template doesn't exist"""
        doc = Document()
        
        # Add title
        title = doc.add_heading(f"{doc_type.replace('_', ' ').title()}", 0)
        
        # Add content based on doc_type
        if doc_type == "offer_letter":
            doc.add_paragraph(f"Customer: {data.customer_name}")
            doc.add_paragraph(f"Facility Type: {data.facility_type}")
            doc.add_paragraph(f"Amount: {data.currency} {data.facility_amount:,.2f}")
            doc.add_paragraph(f"Tenor: {data.tenor} months")
            doc.add_paragraph(f"Profit Rate: {data.profit_rate}%")
            doc.add_paragraph(f"Purpose: {data.purpose}")
        
        return doc
