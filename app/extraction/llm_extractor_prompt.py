"""
LLM-based extraction utilities
"""
from typing import Dict, Optional
import json
from app.services.llm_service import LLMService
from app.schemas.sanction_schema import SanctionData

class LLMExtractor:
    """Extract structured data from text using LLM"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def extract_sanction_data(self, text: str) -> SanctionData:
        """
        Extract sanction letter data using LLM from raw text
        
        Args:
            text: Raw text from sanction letter
            
        Returns:
            SanctionData object with extracted information
        """
        prompt = self._build_extraction_prompt(text)
        extracted_data = self.llm_service.extract_structured_data(prompt)
        
        return SanctionData(**extracted_data)
    
    def extract_sanction_data_from_structured(self, structured_data: Dict) -> SanctionData:
        """
        Extract sanction letter data using LLM from structured data
        This method leverages the separation of tables (facilities) and paragraphs (conditions)
        
        Args:
            structured_data: Dictionary with 'tables' and 'paragraphs' keys
            
        Returns:
            SanctionData object with extracted information including multiple facilities
        """
        prompt = self._build_structured_extraction_prompt(structured_data)
        extracted_data = self.llm_service.extract_structured_data(prompt)
        
        return SanctionData(**extracted_data)
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build prompt for LLM extraction with detailed instructions"""
        return f"""

Role: You are a professional data extraction agent specializing in banking and credit documents.

Task: Extract the following specific data points from the provided text. Map them to the JSON schema provided below.

Context: If a value is not explicitly found, return "Not Found". For the "Facility Matrix", extract all rows found in the "Facility Structure" table.

Desired JSON Structure:

JSON
{
  "entity_info": {
    "obligor_name": "String",
    "registered_address": "String",
    "approved_orr": "String",
    "approver_name": "String (Include Designation)"
  },
  "facility_matrix": [
    {
      "facility_type": "String",
      "limit": "Number (as PKR)",
      "pricing_markup": "String",
      "tenor": "String"
    }
  ],
  "collateral_security": {
    "type": "String",
    "details": "String",
    "value": "Number"
  },
  "critical_covenants": {
    "pre_disbursement": "String",
    "post_disbursement": "String"
  }
}
Constraint: Return ONLY the raw JSON. Do not include conversational text, explanations, or markdown formatting outside of the JSON block.
Source Text: {text}
JSON Response:
        """
    
    def _build_structured_extraction_prompt(self, structured_data: Dict) -> str:
        """Build prompt for LLM extraction using structured data with table/paragraph separation"""
        
        # Format tables for better readability
        tables_text = "\n\n=== TABLES (Sanction Advice / Facility Details) ===\n"
        for i, table in enumerate(structured_data.get('tables', []), 1):
            tables_text += f"\nTable {i}:\n"
            for row in table:
                tables_text += " | ".join(row) + "\n"
        
        # Format paragraphs
        paragraphs_text = "\n\n=== PARAGRAPHS (General Conditions / Terms) ===\n"
        for i, para in enumerate(structured_data.get('paragraphs', []), 1):
            paragraphs_text += f"{i}. {para}\n"
        
        return f"""
Role: You are an expert data extraction agent specializing in Islamic banking and credit sanction documents.

Task: Extract structured sanction data from the provided document that has been pre-processed into TABLES and PARAGRAPHS.
- TABLES contain the Sanction Advice with facility details (multiple facilities may be present)
- PARAGRAPHS contain General Conditions, terms, and narrative text

IMPORTANT: 
1. Extract ALL facilities found in the tables - there may be multiple facilities (Murabaha, Musharaka, etc.)
2. Each facility should be a separate object in the "facilities" array
3. Extract general terms and conditions from the paragraphs section

Expected JSON Schema (Multi-Facility Support):

{{
  "customer_name": "String (Obligor/Customer name)",
  "sanction_date": "String (Date of sanction if found)",
  "facilities": [
    {{
      "facility_type": "String (e.g., Murabaha, Musharaka, LC, etc.)",
      "facility_amount": "String (e.g., 'PKR 50.00 millions')",
      "currency": "String (e.g., 'PKR', 'USD')",
      "tenor": "String (e.g., '36 months', 'At Sight')",
      "profit_rate": "String (e.g., 'KIBOR + 3%')",
      "purpose": "String (Purpose if mentioned)",
      "security": "String (Security/collateral details)"
    }}
  ],
  "terms_conditions": [
    "String (List of key terms and conditions from paragraphs)"
  ]
}}

Instructions:
- Extract customer_name from the document header or table
- For EACH facility row in the tables, create a separate facility object
- Map table columns to facility fields (facility_type, facility_amount, tenor, profit_rate, security)
- Extract all important terms and conditions from the paragraphs as a list
- If a value is not found, use "Not Specified" or null
- Return ONLY valid JSON, no markdown formatting or conversational text

{tables_text}
{paragraphs_text}

JSON Response:
        """
