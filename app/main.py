"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000

Then open:
    http://localhost:8000/docs   ← interactive API docs (test here or in Postman)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="Document Generator API",
    description="Processes Islamic banking sanction letters and generates required charge documents.",
    version="1.0.0",
)

# Allow the frontend (running on a different port/domain) to call this API.
# During development, allow everything. Tighten this before going to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # In production: replace with ["https://yourfrontend.com"]
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "message": "Document Generator API is running.",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/api/v1/health",
    }