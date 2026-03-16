"""
Main FastAPI application entry point
"""
from fastapi import FastAPI
from app.api import routes

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
