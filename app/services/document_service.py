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
from typing import Dict, List
from datetime import datetime
import json
import zipfile
import uuid
import shutil

from app.extraction.docx_parser import DocxParser
from app.extraction.pdf_parser import PDFParser
from app.extraction.llm_extractor import LLMExtractor
from app.services.rule_engine import RuleEngine
from app.utils.docx_generator import DocxGenerator
from app.schemas.sanction_schema import SanctionData
from app.utils.create_templates import main as create_templates_main


class DocumentService:
    """Orchestrate the document generation process."""

    def __init__(self):
        self.docx_parser = DocxParser()
        self.pdf_parser = PDFParser()
        self.llm_extractor = LLMExtractor()   # defaults to "existing" = Gemini
        self.rule_engine = RuleEngine()
        self.docx_generator = DocxGenerator()
        self.output_dir = Path(self.docx_generator.output_dir)
        self.template_dir = Path(self.docx_generator.template_dir)
        self.sessions_dir = self.output_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

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
    async def process_sanction_letter(self, file_content: bytes, filename: str) -> Dict:
        """
        Process a sanction letter uploaded as bytes.
        Supports both PDF and DOCX files.
        """
        if filename.lower().endswith(".pdf"):
            return await self.process_sanction_letter_pdf(file_content)
        elif filename.lower().endswith(".docx"):
            return await self.process_sanction_letter_docx(file_content, filename)
        else:
            return {"success": False, "error": "Unsupported file type. Please upload a .docx or .pdf file."}

    async def process_sanction_letter_and_bundle(self, file_content: bytes, filename: str) -> Dict:
        """
        Process a sanction letter and return a bundled zip of generated docs.
        """
        result = await self.process_sanction_letter(file_content, filename)
        if not result.get("success"):
            return result

        bundle_path = self._create_bundle(result)
        result["bundle_path"] = str(bundle_path)
        return result

    async def process_sanction_letter_session(self, file_content: bytes, filename: str) -> Dict:
        """
        Process a sanction letter and persist generated documents in a session.

        Returns a session payload with document IDs and download URLs.
        """
        result = await self.process_sanction_letter(file_content, filename)
        if not result.get("success"):
            return result

        session_payload = self._create_session(result)
        return {
            "success": True,
            "session": session_payload,
            "sanction_data": result.get("sanction_data"),
            "required_documents": result.get("required_documents"),
        }

    # ------------------------------------------------------------------
    # Shared pipeline
    # ------------------------------------------------------------------

    async def _run_pipeline(self, sanction_data: SanctionData) -> Dict:
        """Validate → determine docs → generate docs."""

        self._ensure_templates()

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_templates(self) -> None:
        """Create starter templates if none exist."""
        docx_files = list(self.template_dir.glob("*.docx"))
        if docx_files:
            return
        create_templates_main()

    def _create_bundle(self, result: Dict) -> Path:
        """Bundle generated documents and metadata into a zip file."""
        generated_files = result.get("generated_files", {})
        all_paths: List[str] = [p for paths in generated_files.values() for p in paths]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_name = f"generated_documents_{timestamp}.zip"
        bundle_path = self.output_dir / bundle_name

        sanction_data = result.get("sanction_data", {})
        required_docs = result.get("required_documents", {})

        sanction_json = self.output_dir / f"sanction_data_{timestamp}.json"
        required_json = self.output_dir / f"required_documents_{timestamp}.json"

        with open(sanction_json, "w", encoding="utf-8") as f:
            json.dump(sanction_data, f, indent=2, ensure_ascii=False, default=str)
        with open(required_json, "w", encoding="utf-8") as f:
            json.dump(required_docs, f, indent=2, ensure_ascii=False, default=str)

        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in all_paths:
                path = Path(file_path)
                if path.exists():
                    zf.write(path, arcname=path.name)
            zf.write(sanction_json, arcname=sanction_json.name)
            zf.write(required_json, arcname=required_json.name)

        return bundle_path

    def _create_session(self, result: Dict) -> Dict:
        """Persist generated files under a session folder and return metadata."""
        generated_files = result.get("generated_files", {})
        all_paths: List[str] = [p for paths in generated_files.values() for p in paths]

        session_id = uuid.uuid4().hex
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        documents = []
        for file_path in all_paths:
            src = Path(file_path)
            if not src.exists():
                continue
            doc_id = uuid.uuid4().hex
            dest_name = f"{doc_id}_{src.name}"
            dest = session_dir / dest_name
            shutil.copyfile(src, dest)
            documents.append({
                "id": doc_id,
                "name": src.name,
                "path": str(dest),
            })

        session_payload = {
            "id": session_id,
            "documents": documents,
        }
        self._write_session_manifest(session_dir, session_payload)
        return session_payload

    def _write_session_manifest(self, session_dir: Path, session_payload: Dict) -> None:
        manifest_path = session_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(session_payload, f, indent=2, ensure_ascii=False, default=str)

    def load_session_manifest(self, session_id: str) -> Dict:
        session_dir = self.sessions_dir / session_id
        manifest_path = session_dir / "manifest.json"
        if not manifest_path.exists():
            return {}
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_session_document_path(self, session_id: str, doc_id: str) -> Path:
        manifest = self.load_session_manifest(session_id)
        for doc in manifest.get("documents", []):
            if doc.get("id") == doc_id:
                return Path(doc.get("path"))
        return Path()