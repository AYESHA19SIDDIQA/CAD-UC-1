"""
API routes — document generation service.

Endpoints
---------
POST /api/v1/process          Upload sanction letter → run full pipeline → return results
GET  /api/v1/health           Server liveness check
GET  /api/v1/download/{name}  Download a generated .docx file by filename
"""
import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.extraction.docx_parser import DocxParser
from app.extraction.llm_extractor import LLMExtractor
from app.services.rule_engine import RuleEngine
from app.utils.docx_generator import DocxGenerator

router = APIRouter(prefix="/api/v1", tags=["documents"])

# Output directory — generated files live here
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── 1. Health check ───────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    """
    Check that the server is running.

    Postman: GET http://localhost:8000/api/v1/health
    Expected response: {"status": "ok"}
    """
    return {"status": "ok"}


# ── 2. Process a sanction letter ──────────────────────────────────────────────

@router.post("/process")
async def process_sanction_letter(file: UploadFile = File(...)):
    """
    Upload a sanction letter (.docx) and run the full pipeline.

    Postman:
      - Method: POST
      - URL: http://localhost:8000/api/v1/process
      - Body → form-data → key: "file", type: File → select your .docx

    Returns JSON with:
      - extracted sanction data
      - list of required documents (by category)
      - list of generated filenames (use /download/{filename} to fetch each)
    """
    # ── validate file type ────────────────────────────────────────────────────
    if not file.filename.endswith((".docx", ".doc")):
        raise HTTPException(
            status_code=400,
            detail=f"Only .docx files are accepted. Got: {file.filename}"
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── step 1: parse ─────────────────────────────────────────────────────────
    try:
        parser = DocxParser()
        structured = parser.extract_structured_data_from_bytes(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse document: {e}")

    # ── step 2: LLM extraction ────────────────────────────────────────────────
    try:
        extractor = LLMExtractor()          # uses "existing" profile = Gemini
        sanction_data = extractor.extract_sanction_data_from_structured(structured)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"LLM extraction failed: {e}")

    # ── step 3: rule engine ───────────────────────────────────────────────────
    engine = RuleEngine()
    required_docs = engine.determine_required_documents(sanction_data)
    validation = engine.validate_sanction_data(sanction_data)

    # ── step 4: generate documents ────────────────────────────────────────────
    try:
        generator = DocxGenerator()
        generated = generator.generate_all_documents(required_docs, sanction_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document generation failed: {e}")

    # Flatten generated paths → just filenames for the response
    # Frontend uses GET /download/{filename} to fetch each file
    generated_filenames = {
        category: [Path(p).name for p in paths]
        for category, paths in generated.items()
    }
    all_filenames = [Path(p).name for paths in generated.values() for p in paths]

    return JSONResponse({
        "success": True,
        "customer_name": sanction_data.customer_name,
        "approval_no": sanction_data.approval_no,
        "sanction_date": str(sanction_data.sanction_date or ""),
        "facilities": [
            {
                "s_no": f.s_no,
                "facility_type": f.facility_type,
                "nature_of_limit": f.nature_of_limit,
                "approved_limit": f.approved_limit,
                "currency": f.currency,
                "tenor": f.tenor,
            }
            for f in sanction_data.facilities
        ],
        "validation": {
            "valid": validation["valid"],
            "total_facilities": validation["total_facilities"],
        },
        "required_documents": required_docs,
        "generated_files": generated_filenames,
        "total_generated": len(all_filenames),
        "download_urls": [
            f"/api/v1/download/{name}" for name in all_filenames
        ],
    })


# ── 3. Download a generated file ──────────────────────────────────────────────

@router.get("/download/{filename}")
def download_file(filename: str):
    """
    Download a generated .docx file by its filename.

    Postman:
      - Method: GET
      - URL: http://localhost:8000/api/v1/download/offer_letter_GlobalTech_20260319.docx
      - Hit Send → click "Save Response" to save the file

    The filename comes from the 'download_urls' list in the /process response.
    """
    # Security: strip path separators so callers can't traverse directories
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {safe_name}. Run /process first."
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe_name,
    )