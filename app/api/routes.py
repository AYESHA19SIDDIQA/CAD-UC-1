"""
API routes for document generation
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.services.document_service import DocumentService
from app.schemas.sanction_schema import SanctionData

router = APIRouter(prefix="/api/v1", tags=["documents"])
document_service = DocumentService()

@router.post("/generate-document")
async def generate_document(file: UploadFile = File(...)):
    """
    Upload a sanction letter (PDF or DOCX) and generate required documents.
    """
    try:
        file_content = await file.read()
        result = await document_service.process_sanction_letter(file_content, file.filename)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-documents-zip")
async def generate_documents_zip(file: UploadFile = File(...)):
    """
    Upload a sanction letter (PDF or DOCX) and return a zip of generated docs.
    """
    try:
        file_content = await file.read()
        result = await document_service.process_sanction_letter_and_bundle(file_content, file.filename)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Processing failed"))

        bundle_path = result.get("bundle_path")
        if not bundle_path:
            raise HTTPException(status_code=500, detail="Bundle generation failed")

        return FileResponse(
            bundle_path,
            media_type="application/zip",
            filename="generated_documents.zip",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-session")
async def generate_session(file: UploadFile = File(...)):
    """
    Upload a sanction letter (PDF or DOCX) and return a session with documents.
    """
    try:
        file_content = await file.read()
        result = await document_service.process_sanction_letter_session(file_content, file.filename)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Processing failed"))

        session = result.get("session", {})
        for doc in session.get("documents", []):
            doc_id = doc.get("id")
            session_id = session.get("id")
            doc["download_url"] = f"/api/v1/sessions/{session_id}/documents/{doc_id}"
            doc["upload_url"] = f"/api/v1/sessions/{session_id}/documents/{doc_id}"

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/documents/{doc_id}")
async def download_session_document(session_id: str, doc_id: str):
    """
    Download a generated document by session/doc id.
    """
    try:
        path = document_service.get_session_document_path(session_id, doc_id)
        if not path or not path.exists():
            raise HTTPException(status_code=404, detail="Document not found")

        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=path.name.split("_", 1)[-1],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/documents/{doc_id}")
async def upload_session_document(session_id: str, doc_id: str, file: UploadFile = File(...)):
    """
    Upload an updated DOCX for a generated document.
    """
    try:
        if not file.filename.lower().endswith(".docx"):
            raise HTTPException(status_code=400, detail="Only .docx files are accepted")

        path = document_service.get_session_document_path(session_id, doc_id)
        if not path or not path.exists():
            raise HTTPException(status_code=404, detail="Document not found")

        content = await file.read()
        path.write_bytes(content)
        return {"success": True, "message": "Document updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
