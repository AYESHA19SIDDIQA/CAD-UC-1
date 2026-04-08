"""
Main FastAPI application entry point and CLI pipeline runner.
"""
import argparse
import asyncio
from pathlib import Path

from fastapi import FastAPI
from app.api import routes
from app.services.document_service import DocumentService

app = FastAPI(
    title="Document Generator API",
    description="API for generating documents from sanction letters",
    version="1.0.0"
)

# Include API routes
app.include_router(routes.router)

@app.get("/")
async def root():
    return {"message": "Document Generator API is running"}


async def _run_pipeline(file_path: Path) -> int:
    service = DocumentService()
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return 1

    file_bytes = file_path.read_bytes()
    result = await service.process_sanction_letter_and_bundle(file_bytes, file_path.name)

    if not result.get("success"):
        print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
        return 1

    print("✅ Processing complete")
    print(f"Bundle: {result.get('bundle_path')}")
    print(f"Total generated: {result.get('total_generated')}")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run document generation pipeline")
    parser.add_argument("--file", type=str, help="Path to sanction document (.docx or .pdf)")
    parser.add_argument("--serve", action="store_true", help="Start the API server")
    args = parser.parse_args()

    if args.file:
        raise SystemExit(asyncio.run(_run_pipeline(Path(args.file))))

    if args.serve or not args.file:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
