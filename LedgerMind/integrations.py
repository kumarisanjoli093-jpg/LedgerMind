
"""
LedgerMind integrations.

Hindsight: persistent vendor memory.
Groq: optional AI-powered vendor communication.
Band AI and OpenClaw: integration status.
"""

import os
import logging
from contextlib import contextmanager
from functools import lru_cache

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "").strip()
HINDSIGHT_BASE_URL = os.getenv(
    "HINDSIGHT_BASE_URL",
    "https://api.hindsight.vectorize.io"
).strip()
HINDSIGHT_BANK_ID = os.getenv(
    "HINDSIGHT_BANK_ID",
    "ledgermind-gst"
).strip()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
).strip()


# --------------------------------------------------
# HINDSIGHT CLIENT
# --------------------------------------------------

@contextmanager
def hindsight_client():

    if not HINDSIGHT_API_KEY:
        raise RuntimeError("HINDSIGHT_API_KEY is not configured.")

    from hindsight_client import Hindsight

    client = Hindsight(
        base_url=HINDSIGHT_BASE_URL,
        api_key=HINDSIGHT_API_KEY
    )

    try:
        try:
            client.create_bank(
                bank_id=HINDSIGHT_BANK_ID,
                name="LedgerMind GST Vendor Memory",
                background=(
                    "Remembers Indian supplier filing behaviour, "
                    "GST reconciliation exceptions, communication "
                    "preferences and verified resolution outcomes."
                ),
                disposition={
                    "skepticism": 4,
                    "literalism": 4,
                    "empathy": 2
                }
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            message = str(exc).lower()

            if status_code != 409 and not any(
                word in message
                for word in ("already exists", "already exist")
            ):
                raise

        yield client

    finally:
        client.close()


# --------------------------------------------------
# SAVE VENDOR MEMORY
# --------------------------------------------------

def remember_vendor_event(vendor: str, content: str):

    if not vendor or not vendor.strip():
        raise ValueError("Vendor name is required.")

    if not content or not content.strip():
        raise ValueError("Memory content is required.")

    try:
        with hindsight_client() as client:

            result = client.retain(
                bank_id=HINDSIGHT_BANK_ID,
                content=f"Vendor: {vendor}. {content}",
                context="LedgerMind GST reconciliation"
            )

            if hasattr(result, "items_count"):
                if result.items_count == 0:
                    raise RuntimeError(
                        "Hindsight did not store any memory."
                    )

            logger.info(
                "Hindsight memory saved for vendor: %s",
                vendor
            )

            return True

    except Exception:
        logger.exception("Hindsight memory save failed.")
        raise


# --------------------------------------------------
# RECALL VENDOR MEMORY
# --------------------------------------------------

def recall_vendor_context(
    vendor: str,
    question: str,
    detailed: bool = False
):

    if not vendor or not vendor.strip():
        raise ValueError("Vendor name is required.")

    try:
        with hindsight_client() as client:

            result = client.recall(
                bank_id=HINDSIGHT_BANK_ID,
                query=f"Vendor {vendor}: {question}",
                budget="mid"
            )

            memories = [
                getattr(item, "text", str(item))
                for item in (result.results or [])
            ]

            return memories if detailed else "\n".join(
                memories[:6]
            )

    except Exception:
        logger.exception("Hindsight memory recall failed.")
        raise


# --------------------------------------------------
# GROQ VENDOR MESSAGE GENERATION
# --------------------------------------------------

def generate_vendor_message(
    row,
    requested_action: str,
    recalled_memory: str,
    fallback: str
):

    if not GROQ_API_KEY:
        return fallback, False

    try:
        from openai import OpenAI

        with OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        ) as client:

            prompt = (
                "Write a concise, professional vendor follow-up "
                "email for an Indian finance team. "
                "Do not invent GST rules, dates, amounts or facts. "
                "Ask for clarification or correction only. "
                "Use prior memory only if relevant. "
                "Return only the email body.\n\n"

                f"Vendor: {row['vendor']}\n"
                f"Period: {row['month']}\n"
                f"Invoice: {row['invoice']}\n"
                f"Exception: {row['issue']}\n"
                f"Details: {row['detail']}\n"
                f"Requested action: {requested_action}\n"
                f"Prior memories: {recalled_memory or 'None'}\n\n"

                "Keep it factual. Do not claim that a message was sent."
            )

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=350
            )

            text = response.choices[0].message.content

            if text and text.strip():
                return text.strip(), True

            return fallback, False

    except Exception:
        logger.exception("Groq message generation failed.")
        return fallback, False


# --------------------------------------------------
# INTEGRATION STATUS
# --------------------------------------------------

def memory_status():

    hindsight_connected = False
    hindsight_error = None

    try:
        with hindsight_client():
            hindsight_connected = True

    except Exception as exc:
        hindsight_error = str(exc)
        logger.warning(
            "Hindsight connection unavailable: %s",
            exc
        )

    return {
        "hindsight": {
            "configured": bool(HINDSIGHT_API_KEY),
            "connected": hindsight_connected,
            "bank_id": HINDSIGHT_BANK_ID,
            "error": hindsight_error
        },
        "groq": {
            "configured": bool(GROQ_API_KEY),
            "model": GROQ_MODEL if GROQ_API_KEY else None
        },
        "band_ai": {
            "required_by_hackathon": True,
            "desktop_app": True,
            "status": "Install and use the Band AI desktop app separately"
        },
        "openclaw": {
            "optional": True,
            "status": "Not enabled; optional Hindsight integration"
        }
    }
