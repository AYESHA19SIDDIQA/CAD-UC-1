"""
LLM-based extraction utilities.

Single source of truth — replaces both llm_extractor.py and llm_extractor_prompt.py.
"""
from typing import Dict
from app.services.llm_service import LLMService
from app.schemas.sanction_schema import SanctionData


class LLMExtractor:
    """Extract structured SanctionData from raw or pre-parsed document content."""

    def __init__(self, model_profile: str = "existing"):
        """
        Args:
            model_profile: LLMService profile to use.
                "existing" → whatever provider/model is set in .env (Gemini by default).
                "qwen_small_local" → local CPU model (only if transformers is installed).
        """
        self.llm_service = LLMService()
        self.model_profile = model_profile

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def extract_sanction_data(self, text: str) -> SanctionData:
        """Extract from raw plain text (fallback path)."""
        prompt = self._build_raw_text_prompt(text)
        data = self.llm_service.extract_structured_data(prompt, model_profile=self.model_profile)
        return SanctionData(**data)

    def extract_sanction_data_from_structured(self, structured_data: Dict) -> SanctionData:
        """
        Extract from pre-parsed structured data (preferred path).

        structured_data must have keys:
            "tables"     – list of table rows from DocxParser
            "paragraphs" – list of paragraph strings from DocxParser
        """
        prompt = self._build_structured_prompt(structured_data)
        data = self.llm_service.extract_structured_data(prompt, model_profile=self.model_profile)
        return SanctionData(**data)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_raw_text_prompt(self, text: str) -> str:
        return f"""
You are an expert data extraction agent specialising in Islamic banking and credit sanction documents.

Extract structured sanction data from the raw text below and return ONLY valid JSON — no markdown, no explanation.

Expected JSON schema:
{{
  "approval_no": "string or null",
  "proposal_type": "string or null",
  "approval_level": "string or null",
  "sanction_date": "string or null",
  "customer_name": "string",
  "customer_location": "string or null",
  "business_segment": "string or null",
  "icrr": "string or null",
  "originating_unit_region": "string or null",
  "facilities": [
    {{
      "s_no": "integer or null",
      "nature_of_limit": "string",
      "facility_type": "string  (e.g. LC, Murabaha, Musharaka)",
      "existing_limit": "string or null",
      "approved_limit": "string",
      "increase_decrease": "string or null",
      "currency": "string (default PKR)",
      "profit_rate": "string",
      "tenor": "string",
      "expiry_review": "string or null",
      "purpose": "string or null",
      "security": "string",
      "is_sub_limit": false,
      "parent_facility_s_no": null
    }}
  ],
  "terms_conditions": ["string", ...]
}}

Raw document text:
{text}

JSON:"""

    def _build_structured_prompt(self, structured_data: Dict) -> str:
        # Format tables
        tables_block = "\n=== TABLES (facility details) ===\n"
        for i, table in enumerate(structured_data.get("tables", []), 1):
            tables_block += f"\nTable {i}:\n"
            for row in table:
                tables_block += " | ".join(str(c) for c in row) + "\n"

        # Format paragraphs
        paras_block = "\n=== PARAGRAPHS (conditions / header info) ===\n"
        for i, para in enumerate(structured_data.get("paragraphs", []), 1):
            paras_block += f"{i}. {para}\n"

        return f"""
You are an expert data extraction agent specialising in Islamic banking and credit sanction documents.

The document has been pre-processed into TABLES and PARAGRAPHS:
- TABLES contain the facility structure (one row per facility line).
- PARAGRAPHS contain header information, general conditions, and special notes.

CRITICAL RULES:
1. Extract EVERY facility row from the tables as a separate object in "facilities".
2. For the "facility_type" field use the short canonical name only: "LC", "Murabaha",
   "Musharaka", "Ijarah", "Diminishing Musharaka", or "Bank Guarantee". Do NOT copy the
   full nature-of-limit description into facility_type.
3. Set "is_sub_limit": true and "parent_facility_s_no" for any row whose nature_of_limit
   says "Sub Limit of Facility N".
4. Extract header fields (approval_no, customer_name, etc.) from paragraphs that appear
   before the tables.
5. Return ONLY valid JSON — no markdown, no prose.

Expected JSON schema:
{{
  "approval_no": "string or null",
  "proposal_type": "string or null",
  "approval_level": "string or null",
  "sanction_date": "string or null",
  "customer_name": "string",
  "customer_location": "string or null",
  "business_segment": "string or null",
  "icrr": "string or null",
  "originating_unit_region": "string or null",
  "facilities": [
    {{
      "s_no": 1,
      "nature_of_limit": "full text from table",
      "facility_type": "LC",
      "existing_limit": "50.00",
      "approved_limit": "50.00",
      "increase_decrease": "-",
      "currency": "PKR",
      "profit_rate": "85% Commission on opening, PAD: K+3%",
      "tenor": "At Sight",
      "expiry_review": "Review",
      "purpose": "Import financing",
      "security": "100% cash backed, Letter of Lien and Set-off, Lien over Import Documents",
      "is_sub_limit": false,
      "parent_facility_s_no": null
    }}
  ],
  "terms_conditions": ["string", ...]
}}

{tables_block}
{paras_block}

JSON:"""