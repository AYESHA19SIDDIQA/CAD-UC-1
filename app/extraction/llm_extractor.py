"""
LLM-based extraction utilities — v2.
Single source of truth. Fixes:
  - Security pulled from TABLE 3 (Security Arrangements), not guessed
  - terms_conditions filtered to real obligation sentences only
  - Default model profile = "existing" (Gemini), not local Qwen
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
      "approved_limit_words": "string (e.g. '50.00' -> 'Fifty Million Rupees')",
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
        """
        Build an extraction prompt that explicitly separates the three tables:
          Table 1 — header info (approval no, customer, date, etc.)
          Table 2 — facility structure (limits, profit, tenor)
          Table 3 — security arrangements (one row per facility)

        And filters paragraphs to extract only real conditions, not headings.
        """
        tables = structured_data.get("tables", [])
        paragraphs = structured_data.get("paragraphs", [])

        # ── Format each table with its index clearly labelled ──────────
        tables_block = ""
        for i, table in enumerate(tables, 1):
            tables_block += f"\n--- TABLE {i} ---\n"
            for row in table:
                tables_block += " | ".join(str(c).replace("\n", " / ") for c in row) + "\n"

        # ── Filter paragraphs: keep only real condition sentences ──────
        HEADING_MARKERS = {
            "sanction advice", "details of facilities", "security arrangements",
            "special conditions", "special notes", "general conditions",
            "pg of directors", "facility structure", "funded and non funded",
            "total non funded", "total funded",
        }
        condition_paras = []
        for para in paragraphs:
            stripped = para.strip()
            if len(stripped) < 15:
                continue
            if any(marker in stripped.lower() for marker in HEADING_MARKERS):
                continue
            # Skip signature / location lines
            if len(stripped) < 80 and stripped.endswith(("Karachi", "Manager", "East")):
                continue
            condition_paras.append(stripped)

        paras_block = "\n".join(
            f"{i}. {p}" for i, p in enumerate(condition_paras, 1)
        )

        return f"""
You are an expert data extraction agent specialising in Islamic banking and
credit sanction documents.

The document has been pre-processed into three TABLES and a list of PARAGRAPHS.
Read the table descriptions carefully before extracting.

TABLE DESCRIPTIONS
==================
TABLE 1 — Document header
  Contains: Approval No, Proposal Type, Approval Level, Date,
            Customer Name and Location, Business Segment, ICRR,
            Originating Unit / Region.

TABLE 2 — Facility Structure
  Columns (in order): S.No | Nature of Limit | Existing Limits |
                      Approved Limits | Increase/(Decrease) |
                      Profit | Tenor | Expiry/Review
  Each data row = one facility. Skip header rows (e.g. "Facility Structure",
  "S. No", "Funded and Non Funded Exposure", "Total" rows).

TABLE 3 — Security Arrangements
  Two columns: [Facility Name] | [Security bullet points]
  Each row = security details for one facility.
  The security text contains multiple bullet points separated by " / ".
  Match each row to the correct facility by comparing the facility name
  in column 1 to the nature_of_limit in TABLE 2.

PARAGRAPHS — General Conditions only
  These are actual obligation sentences from the document.
  Do NOT include section headings, table captions, or signature lines.

EXTRACTION RULES
================
1. Extract ALL facility rows from TABLE 2 as separate objects in "facilities".
2. The document specifies limits are in "PKR millions". Convert these values to their full numeric representation. For example, "50.00" should become "50000000".
3. For "facility_type" use ONLY the short canonical name:
   "LC", "Murabaha", "Musharaka", "Ijarah", "Diminishing Musharaka",
   or "Bank Guarantee". Do NOT copy the full nature_of_limit text.
4. For "security" on each facility: look up the matching row in TABLE 3
   using the facility name. Copy the FULL security text (all bullet points
   joined with "; "). If no match found, use the security text from the
   nearest matching row.
5. Set "is_sub_limit": true and "parent_facility_s_no" for any facility
   whose nature_of_limit contains "Sub Limit of Facility N".
6. For "terms_conditions": include ONLY actual obligation/condition
   sentences from the PARAGRAPHS list. Do NOT include:
   - Section headings ("General Conditions", "Special Notes", etc.)
   - Table captions ("Details of Facilities in PKR millions")
   - Signature lines or names
   A real condition typically starts with a verb or noun and ends with
   a full stop.
7. For "approved_limit_words", convert the numeric "approved_limit" into words.
   The document specifies limits are in "PKR millions".
   Example: "50.00" becomes "Fifty Million Rupees".
8. Return ONLY valid JSON — no markdown, no prose, no explanation.

EXPECTED JSON SCHEMA
====================
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
      "nature_of_limit": "LC Sight (Foreign) under MSFA",
      "facility_type": "LC",
      "existing_limit": "50000000",
      "approved_limit": "50000000",
      "approved_limit_words": "Fifty Million Rupees",
      "increase_decrease": "-",
      "currency": "PKR",
      "profit_rate": "85% Commission on opening / 75% Commission on retirement / PAD: K+3%",
      "tenor": "At Sight",
      "expiry_review": "Review",
      "purpose": "Import financing",
      "security": "100% cash backed in form of Cash margin / Lien over MBL Deposit / Director Accounts maintained with KDLB Branch; Letter of Lien & Set-off; Lien over Import Documents; PG of Directors / Deposit Holder",
      "is_sub_limit": false,
      "parent_facility_s_no": null
    }}
  ],
  "terms_conditions": [
    "Confirmation in writing as to acceptance of approval is obtained from the customer before allowing facilities.",
    "Ensure proper compliance of Prudential Regulations, bank policy and SBP guidelines issued from time to time."
  ]
}}

DOCUMENT DATA
=============
{tables_block}

CONDITION PARAGRAPHS
====================
{paras_block}

JSON:"""