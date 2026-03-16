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
        Extract sanction letter data using LLM
        
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
You are an expert at extracting information from bank sanction letters and loan documents.

Extract the following information from the sanction letter below and return it as a valid JSON object.

Required fields to extract:
- customer_name: The name of the customer/borrower
- facility_type: Type of facility (e.g., Working Capital, Term Loan, Overdraft, etc.)
- facility_amount: The sanctioned amount with currency
- tenor: Duration/tenure of the facility
- profit_rate: Interest rate or profit rate
- purpose: Purpose of the facility/loan
- security: Security/collateral details
- terms_and_conditions: Key terms and conditions (as a list)

IMPORTANT:
1. Extract exact values as they appear in the document
2. If a field is not found, use null for that field
3. For terms_and_conditions, extract as an array of strings
4. Return ONLY valid JSON, no additional text or markdown

Sanction Letter Text:
{text}

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
