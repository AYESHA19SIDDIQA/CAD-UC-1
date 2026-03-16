"""
API routes for document generation
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.document_service import DocumentService
from app.schemas.sanction_schema import SanctionData

router = APIRouter(prefix="/api/v1", tags=["documents"])
document_service = DocumentService()

@router.post("/generate-document")
async def generate_document(file: UploadFile = File(...)):
    """
    Upload a sanction letter PDF and generate required documents
    """
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")
        
        pdf_content = await file.read()
        result = await document_service.process_sanction_letter(pdf_content)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
