"""
LLM-based extraction utilities
"""
from typing import Dict, Optional
import json
from app.services.llm_service import LLMService
from app.schemas.sanction_schema import SanctionData

class LLMExtractor:
    """Extract structured data from text using LLM"""

    def __init__(self, model_profile: str = "qwen_small_local"):
        self.llm_service = LLMService()
        self.model_profile = model_profile
    
    def extract_sanction_data(self, text: str) -> SanctionData:
        """
        Extract sanction letter data using LLM
        
        Args:
            text: Raw text from sanction letter
            
        Returns:
            SanctionData object with extracted information
        """
        prompt = self._build_extraction_prompt(text)
        extracted_data = self.llm_service.extract_structured_data(prompt, model_profile=self.model_profile)

        return SanctionData(**extracted_data)

    def extract_sanction_data_from_structured(self, structured_data: Dict) -> SanctionData:
        """
        Extract sanction letter data using LLM
        This method leverages the separation of tables (facilities) and paragraphs (conditions)

        Args:
            structured_data: Dictionary with 'tables' and 'paragraphs' keys

        Returns:
            SanctionData object with extracted information including multiple facilities
        """
        prompt = self._build_structured_extraction_prompt(structured_data)
        extracted_data = self.llm_service.extract_structured_data(prompt, model_profile=self.model_profile)

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
- TABLES contain the Sanction Advice with facility details (multiple facilities may be present). The table columns typically include:
    S. No, Nature of Limit, Existing Limits, Approved Limits, Increase/(Decrease), Profit, Tenor, Expiry/Review.
- PARAGRAPHS contain General Conditions, terms, and narrative text. Also look for header information before the tables (approval number, proposal type, approval level, date, customer name and location, business segment, ICRR, originating unit).

IMPORTANT:
1. Extract ALL facilities found in the tables - there may be multiple facilities (Murabaha, Musharaka, LC, etc.).
2. For each facility, create a separate object in the "facilities" array.
3. Identify if a facility is a sub-limit (e.g., "Sub Limit of Facility 1") and set "is_sub_limit" to true, and store the parent facility's serial number in "parent_facility_s_no".
4. Extract general terms and conditions from the paragraphs section as a list of strings.
5. Extract all header fields from the paragraphs that appear before the tables.

Expected JSON Schema (Multi-Facility Support with Detailed Fields):

{{
  "approval_no": "String (e.g., 'CBD/level#03/2018/0090/18/12/2018')",
  "proposal_type": "String (e.g., 'Renewal', 'Fresh')",
  "approval_level": "String (e.g., 'Level3')",
  "sanction_date": "String (Date of sanction, e.g., 'December 18, 2018')",
  "customer_name": "String (Obligor/Customer name)",
  "customer_location": "String (Customer's address/location)",
  "business_segment": "String (e.g., 'ME')",
  "icrr": "String (e.g., '3 - Good')",
  "originating_unit_region": "String (e.g., 'Shahrah e Faisal Karachi')",
  "facilities": [
    {{
      "s_no": "Integer or String (Serial number from table)",
      "nature_of_limit": "String (Full description, e.g., 'LC Sight (Foreign) under MSFA')",
      "facility_type": "String (Normalized type, e.g., 'LC', 'Murabaha', 'Musharaka')",
      "existing_limit": "String (e.g., '50.00')",
      "approved_limit": "String (e.g., '50.00')",
      "increase_decrease": "String (e.g., '-', '+5.00')",
      "currency": "String (e.g., 'PKR', 'USD')",
      "profit_rate": "String (e.g., '85% Commission on opening, 75% Commission on retirement, PAD: K+3%')",
      "tenor": "String (e.g., '36 months', 'At Sight', 'Max 120 Days')",
      "expiry_review": "String (e.g., 'Review', 'Fresh')",
      "purpose": "String (Purpose if mentioned, otherwise empty)",
      "security": "String (Security/collateral details, combine if multiple)",
      "is_sub_limit": "Boolean (true if this is a sub-limit, false otherwise)",
      "parent_facility_s_no": "Integer or null (if sub-limit, the s_no of the main facility)"
    }}
  ],
  "terms_conditions": [
    "String (List of key terms and conditions from paragraphs)"
  ]
}}

Instructions:
- Extract header information from the paragraphs that appear before the tables (often at the very beginning).
- For each facility row in the tables, map the columns as follows:
    - Column 1 (S. No) -> "s_no"
    - Column 2 (Nature of Limit) -> "nature_of_limit" and also derive "facility_type" from it.
    - Column 3 (Existing Limits) -> "existing_limit"
    - Column 4 (Approved Limits) -> "approved_limit"
    - Column 5 (Increase/(Decrease)) -> "increase_decrease"
    - Column 6 (Profit) -> "profit_rate"
    - Column 7 (Tenor) -> "tenor"
    - Column 8 (Expiry/Review) -> "expiry_review"
- Look for security information in the paragraphs or in a separate security section; combine multiple items into one string.
- If a field is not found, use an empty string or null as appropriate.
- Return ONLY valid JSON, no markdown formatting or conversational text.

{tables_text}
{paragraphs_text}

JSON Response:
        """
