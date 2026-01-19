from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.scan import router as scan_router

app = FastAPI(
    title="BlockScope API",
    description="Smart Contract Vulnerability Scanner",
    version="0.1.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to localhost:3000 in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {"message": "BlockScope API", "version": "0.1.0"}

# Include routers
app.include_router(scan_router)
