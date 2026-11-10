"""Optional Hindsight + Groq adapters for LedgerMind.

Hindsight is the persistent memory layer. Groq is the optional LLM provider.
The core reconciliation engine remains deterministic and works without API keys.
"""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "").strip()
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").strip()
HINDSIGHT_BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "ledgermind-gst").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

@lru_cache(maxsize=1)
def hindsight_client():
    if not HINDSIGHT_API_KEY:
        return None
    try:
        from hindsight_client import Hindsight
        client = Hindsight(base_url=HINDSIGHT_BASE_URL, api_key=HINDSIGHT_API_KEY)
        try:
            client.create_bank(
                bank_id=HINDSIGHT_BANK_ID,
                name="LedgerMind GST Vendor Memory",
                background="Remembers Indian supplier filing behaviour, GST reconciliation exceptions, communication preferences and verified resolution outcomes.",
                disposition={"skepticism": 4, "literalism": 4, "empathy": 2}
            )
        except Exception as exc:
            # Existing bank is expected on subsequent startups. Other failures surface in status.
            status_code = getattr(exc, "status_code", None)
            if status_code != 409 and "exist" not in str(exc).lower() and "already" not in str(exc).lower():
                raise
        return client
    except Exception:
        return None

def remember_vendor_event(vendor: str, content: str):
    client = hindsight_client()
    if not client: return False
    try:
        client.retain(bank_id=HINDSIGHT_BANK_ID, content=f"Vendor: {vendor}. {content}", context="GST reconciliation cycle")
        return True
    except Exception:
        return False

def recall_vendor_context(vendor: str, question: str, detailed: bool=False):
    client = hindsight_client()
    if not client: return [] if detailed else ""
    try:
        result = client.recall(bank_id=HINDSIGHT_BANK_ID, query=f"Vendor {vendor}: {question}", budget="mid")
        memories = [getattr(x, "text", str(x)) for x in (getattr(result, "results", []) or [])]
        return memories if detailed else "\n".join(memories[:6])
    except Exception:
        return [] if detailed else ""

def generate_vendor_message(row, requested_action: str, recalled_memory: str, fallback: str):
    if not GROQ_API_KEY:
        return fallback, False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        prompt = (
            "Write a concise, professional vendor follow-up email for an Indian finance team. "
            "Do not invent GST rules, dates, amounts or facts. Ask for clarification/correction only. "
            "Use prior memory only if relevant. Return only the email body.\n\n"
            f"Vendor: {row['vendor']}\nPeriod: {row['month']}\nInvoice: {row['invoice']}\n"
            f"Exception: {row['issue']}\nDetails: {row['detail']}\n"
            f"Requested action: {requested_action}\nPrior Hindsight memories: {recalled_memory or 'No relevant memories found.'}\n"
            "Keep it factual and do not claim a message was sent."
        )
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            max_tokens=350
        )
        text = response.choices[0].message.content
        return (text.strip(), True) if text and text.strip() else (fallback, False)
    except Exception:
        # LLM/API/tool failures must never stop reconciliation; deterministic draft is fallback.
        return fallback, False

def memory_status():
    h = hindsight_client()
    return {
        "hindsight": {"configured": bool(HINDSIGHT_API_KEY), "connected": h is not None, "bank_id": HINDSIGHT_BANK_ID if h else None},
        "groq": {"configured": bool(GROQ_API_KEY), "model": GROQ_MODEL if GROQ_API_KEY else None},
        "band_ai": {"required_by_hackathon": True, "desktop_app": True, "status": "Install and use the Band AI desktop app separately"},
        "openclaw": {"optional": True, "status": "Not enabled; optional Hindsight integration"}
    }
