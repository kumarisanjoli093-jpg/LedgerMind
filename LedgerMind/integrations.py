# integrations.py
import os
import logging
from dotenv import load_dotenv

load_dotenv()

try:
    from hindsight_client import Hindsight
except ImportError:
    Hindsight = None

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "").strip()
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").strip()
HINDSIGHT_BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "ledgermind-gst").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

_hindsight_client = None

def get_hindsight_client():
    """Safely initializes the Hindsight client."""
    global _hindsight_client
    if _hindsight_client is None:
        api_key = os.getenv("HINDSIGHT_API_KEY", "").strip() or HINDSIGHT_API_KEY
        if not api_key:
            logger.warning("HINDSIGHT_API_KEY is not set.")
            return None
        
        if Hindsight is None:
            logger.error("Hindsight SDK is not installed.")
            return None
            
        try:
            _hindsight_client = Hindsight(
                base_url=HINDSIGHT_BASE_URL,
                api_key=api_key,
                timeout=10.0,
                max_attempts=2
            )
            logger.info("Hindsight API client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Hindsight client: {e}")
            return None
            
    return _hindsight_client

def remember_interaction(text: str, metadata: dict = None):
    """Saves chat or general interaction data to Hindsight memory."""
    client = get_hindsight_client()
    if not client:
        return False
        
    try:
        bank_id = os.getenv("HINDSIGHT_BANK_ID", "").strip() or HINDSIGHT_BANK_ID
        client.retain(bank_id=bank_id, content=text, context="User chat interaction")
        return True
    except Exception as e:
        logger.error(f"Hindsight storage failed: {e}")
        return False

def recall_context(query: str, limit: int = 3):
    """Retrieves relevant past memories for chat or query context."""
    client = get_hindsight_client()
    if not client:
        return []
        
    try:
        bank_id = os.getenv("HINDSIGHT_BANK_ID", "").strip() or HINDSIGHT_BANK_ID
        result = client.recall(bank_id=bank_id, query=query, budget="mid")
        memories = [getattr(x, "text", str(x)) for x in (getattr(result, "results", []) or [])]
        return memories[:limit]
    except Exception as e:
        logger.error(f"Hindsight recall failed: {e}")
        return []

# =====================================================================
# VENDOR RECONCILIATION & MAIN.PY INTEGRATION FUNCTIONS
# =====================================================================

def memory_status(*args, **kwargs):
    """Returns the live status of integrations as expected by the frontend dashboard."""
    api_key = os.getenv("HINDSIGHT_API_KEY", "").strip() or HINDSIGHT_API_KEY
    groq_key = os.getenv("GROQ_API_KEY", "").strip() or GROQ_API_KEY
    bank_id = os.getenv("HINDSIGHT_BANK_ID", "").strip() or HINDSIGHT_BANK_ID
    groq_model = os.getenv("GROQ_MODEL", "").strip() or GROQ_MODEL
    client = get_hindsight_client()
    return {
        "hindsight": {
            "configured": bool(api_key),
            "connected": client is not None,
            "bank_id": bank_id if client else None
        },
        "groq": {
            "configured": bool(groq_key),
            "model": (groq_model or "openai/gpt-oss-120b") if groq_key else None
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

def remember_vendor_event(vendor: str, event: str, *args, **kwargs):
    """Records vendor filing and reconciliation events in Hindsight memory."""
    client = get_hindsight_client()
    if not client:
        return False
    try:
        bank_id = os.getenv("HINDSIGHT_BANK_ID", "").strip() or HINDSIGHT_BANK_ID
        client.retain(bank_id=bank_id, content=f"Vendor: {vendor}. {event}", context="GST reconciliation cycle")
        return True
    except Exception as e:
        logger.error(f"Failed to record vendor event for {vendor}: {e}")
        return False

def recall_vendor_context(vendor: str, question: str = "", detailed: bool = False, *args, **kwargs):
    """Recalls vendor filing behaviour and prior exception patterns."""
    client = get_hindsight_client()
    if not client:
        return [] if detailed else ""
    try:
        bank_id = os.getenv("HINDSIGHT_BANK_ID", "").strip() or HINDSIGHT_BANK_ID
        query = f"Vendor {vendor}: {question}".strip()
        result = client.recall(bank_id=bank_id, query=query, budget="mid")
        memories = [getattr(x, "text", str(x)) for x in (getattr(result, "results", []) or [])]
        return memories if detailed else "\n".join(memories[:6])
    except Exception as e:
        logger.error(f"Failed to recall vendor context for {vendor}: {e}")
        return [] if detailed else ""

def generate_vendor_message(row_data, ask, recalled, fallback, *args, **kwargs):
    """Generates a contextual vendor message via Groq LLM with deterministic fallback."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip() or GROQ_API_KEY
    if not groq_key:
        return fallback, False
    try:
        from openai import OpenAI
        groq_model = os.getenv("GROQ_MODEL", "").strip() or GROQ_MODEL or "openai/gpt-oss-120b"
        client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
        prompt = (
            "Write a concise, professional vendor follow-up email for an Indian finance team. "
            "Do not invent GST rules, dates, amounts or facts. Ask for clarification/correction only. "
            "Use prior memory only if relevant. Return only the email body.\n\n"
            f"Vendor: {row_data['vendor']}\nPeriod: {row_data['month']}\nInvoice: {row_data['invoice']}\n"
            f"Exception: {row_data['issue']}\nDetails: {row_data['detail']}\n"
            f"Requested action: {ask}\nPrior Hindsight memories: {recalled or 'No relevant memories found.'}\n"
            "Keep it factual and do not claim a message was sent."
        )
        response = client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=350
        )
        text = response.choices[0].message.content
        return (text.strip(), True) if text and text.strip() else (fallback, False)
    except Exception as e:
        logger.warning(f"Groq LLM draft generation failed, using fallback: {e}")
        return fallback, False
