"""
Main document generation service — orchestrates the full pipeline.

Pipeline
--------
1. Parse the uploaded file (DOCX or PDF) into tables + paragraphs.
2. Send structured data to the LLM to extract SanctionData.
3. Validate the result with RuleEngine.
4. Determine which documents are required.
5. Generate each document via DocxGenerator.
6. Return results.
"""
from pathlib import Path
from typing import Dict

from app.extraction.docx_parser import DocxParser
from app.extraction.pdf_parser import PDFParser
from app.extraction.llm_extractor import LLMExtractor
from app.services.rule_engine import RuleEngine
from app.utils.docx_generator import DocxGenerator
from app.schemas.sanction_schema import SanctionData


class DocumentService:
    """Orchestrate the document generation process."""

    def __init__(self):
        self.docx_parser = DocxParser()
        self.pdf_parser = PDFParser()
        self.llm_extractor = LLMExtractor()   # defaults to "existing" = Gemini
        self.rule_engine = RuleEngine()
        self.docx_generator = DocxGenerator()

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    async def process_sanction_letter_docx(self, file_content: bytes, filename: str) -> Dict:
        """
        Process a DOCX sanction letter uploaded as bytes.

        Args:
            file_content: Raw bytes of the .docx file.
            filename:     Original filename (used for naming output files).

        Returns:
            Result dict with success flag, extracted data, and generated file paths.
        """
        # Step 1: Parse DOCX into structured tables + paragraphs
        structured_data = self.docx_parser.extract_structured_data_from_bytes(file_content)

        # Step 2: LLM extraction
        try:
            sanction_data = self.llm_extractor.extract_sanction_data_from_structured(structured_data)
        except Exception as exc:
            return {"success": False, "error": f"LLM extraction failed: {exc}"}

        return await self._run_pipeline(sanction_data)

    async def process_sanction_letter_pdf(self, pdf_content: bytes) -> Dict:
        """
        Process a PDF sanction letter uploaded as bytes.

        Falls back to raw-text extraction (less accurate than DOCX path).
        """
        text = self.pdf_parser.extract_text(pdf_content)
        try:
            sanction_data = self.llm_extractor.extract_sanction_data(text)
        except Exception as exc:
            return {"success": False, "error": f"LLM extraction failed: {exc}"}

        return await self._run_pipeline(sanction_data)

    # Keep old method name for backward compatibility with existing routes
    async def process_sanction_letter(self, pdf_content: bytes) -> Dict:
        return await self.process_sanction_letter_pdf(pdf_content)

    # ------------------------------------------------------------------
    # Shared pipeline
    # ------------------------------------------------------------------

    async def _run_pipeline(self, sanction_data: SanctionData) -> Dict:
        """Validate → determine docs → generate docs."""

        # Step 3: Validate
        validation = self.rule_engine.validate_sanction_data(sanction_data)
        if not validation["valid"]:
            # Non-fatal: log issues but continue so we still generate what we can
            print(f"[DocumentService] Validation issues: {validation}")

        # Step 4: Determine required documents
        required_docs = self.rule_engine.determine_required_documents(sanction_data)

        # Step 5: Generate documents
        generated = self.docx_generator.generate_all_documents(required_docs, sanction_data)

        # Flatten all paths for convenience
        all_paths = [p for paths in generated.values() for p in paths]

        return {
            "success": True,
            "sanction_data": sanction_data.model_dump(mode="json"),
            "validation": validation,
            "required_documents": required_docs,
            "generated_files": generated,
            "total_generated": len(all_paths),
        }