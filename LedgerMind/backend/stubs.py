from decimal import Decimal

def extract_receipt(file_bytes: bytes, filename: str) -> dict:
    """Stub for Member 1: AI Agent & RAG"""
    return {
        "vendor": "Stub Vendor Pvt Ltd",
        "date": "2026-11-11",
        "taxable_amount": 1000.00,
        "tax_amount": 180.00,
        "total_amount": 1180.00,
        "gstin": "29ABCDE1234F1Z5"
    }

def answer_question(question: str) -> dict:
    """Stub for Member 1: AI Agent & RAG"""
    return {
        "answer": f"This is a stub answer to your question: '{question}'. Hindsight memory recalled 2 past transactions.",
        "sources": ["transaction_45", "receipt_12"]
    }

def calculate_gst(taxable: float, rate: float, supplier_state: str, buyer_state: str) -> dict:
    """Stub for Member 4: GST Engine"""
    taxable_dec = Decimal(str(taxable))
    rate_dec = Decimal(str(rate))
    
    tax = taxable_dec * (rate_dec / Decimal("100"))
    
    if supplier_state.strip().upper() == buyer_state.strip().upper():
        return {
            "cgst": float(tax / 2),
            "sgst": float(tax / 2),
            "igst": 0.0
        }
    return {
        "cgst": 0.0,
        "sgst": 0.0,
        "igst": float(tax)
    }

def validate_invoice(invoice: dict) -> list[str]:
    """Stub for Member 4: GST Engine"""
    errors = []
    if "taxable" not in invoice or invoice["taxable"] < 0:
        errors.append("Invalid or missing taxable amount.")
    if "gstin" not in invoice or len(invoice.get("gstin", "")) != 15:
        errors.append("Invalid GSTIN format.")
    return errors