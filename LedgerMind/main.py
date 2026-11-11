
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ai_agent.api_routes import router as ai_router
from integrations import memory_status


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# PROJECT DIRECTORIES
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="LedgerMind GST Agent",
    description=(
        "AI-powered GST invoice extraction, "
        "reconciliation and financial assistance."
    ),
    version="2.0.0",
)


# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

allowed_origins = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in allowed_origins
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# SERVE FRONTEND STATIC FILES
# --------------------------------------------------

if STATIC_DIR.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )
else:
    logger.warning("Static directory not found: %s", STATIC_DIR)


# --------------------------------------------------
# REGISTER AI ROUTES
# --------------------------------------------------

app.include_router(ai_router)


# --------------------------------------------------
# ROOT ENDPOINT — LEDGERMIND WEBSITE
# --------------------------------------------------

@app.get("/")
async def root():
    index_file = TEMPLATES_DIR / "index.html"

    if not index_file.is_file():
        return {
            "success": False,
            "application": "LedgerMind",
            "error": "Frontend index.html was not found.",
        }

    return FileResponse(
        path=str(index_file),
        media_type="text/html",
    )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
async def health_check():
    return {
        "success": True,
        "status": "healthy",
        "application": "LedgerMind",
    }


# --------------------------------------------------
# AI AGENT STATUS
# --------------------------------------------------

@app.get("/api/ai/status")
async def ai_status():
    hindsight_connected = False

    try:
        status = memory_status()
        hindsight_connected = bool(status)
    except Exception:
        logger.exception("Could not retrieve Hindsight status.")

    return {
        "success": True,
        "agent": "LedgerMind",
        "rag_available": True,
        "hindsight_status": (
            "available" if hindsight_connected else "unavailable"
        ),
    }


# --------------------------------------------------
# APPLICATION STARTUP
# --------------------------------------------------

@app.on_event("startup")
async def startup_event():
    logger.info("LedgerMind API starting...")
    logger.info("Project directory: %s", BASE_DIR)
    logger.info("Frontend directory: %s", TEMPLATES_DIR)
    logger.info("Static directory: %s", STATIC_DIR)
    logger.info("AI routes registered successfully.")


# --------------------------------------------------
# APPLICATION SHUTDOWN
# --------------------------------------------------

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("LedgerMind API shutting down...")
