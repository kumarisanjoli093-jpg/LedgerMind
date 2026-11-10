
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
# REGISTER AI ROUTES
# --------------------------------------------------

app.include_router(ai_router)


# --------------------------------------------------
# ROOT ENDPOINT
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "success": True,
        "application": "LedgerMind",
        "version": "2.0.0",
        "message": "LedgerMind API is running.",
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "success": True,
        "status": "healthy",
        "application": "LedgerMind",
    }


# --------------------------------------------------
# AI AGENT STATUS
# --------------------------------------------------

@app.get("/api/ai/status")
def ai_status():

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
    logger.info("AI routes registered successfully.")


# --------------------------------------------------
# APPLICATION SHUTDOWN
# --------------------------------------------------

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("LedgerMind API shutting down...")
