"""
Main FastAPI Application Entrypoint
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import init_db
from backend.app.api.v1.router import api_router
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    logger.info("Starting Oil Spill Intelligence System backend...")
    init_db()
    yield
    logger.info("Shutting down backend...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Satellite SAR Oil Spill Detection, Trajectory Forecasting, Impact Assessment & Decision-Support System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Global Exception Handler for structured JSON errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc)
            }
        }
    )

# Include versioned API router
app.include_router(api_router)

os.makedirs("temp_downloads", exist_ok=True)
app.mount("/static/images", StaticFiles(directory="temp_downloads"), name="images")

@app.get("/")
def root():
    return {
        "system": settings.APP_NAME,
        "version": "1.0.0",
        "status": "OPERATIONAL",
        "api_docs": "/docs",
        "api_prefix": "/api/v1"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
