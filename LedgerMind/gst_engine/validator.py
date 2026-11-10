import re
from decimal import Decimal
from gst_engine.constants import STATE_CODES, VALID_GST_RATES

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

def validate_gstin(gstin: str) -> bool:
    """Validates 15-character Indian GSTIN format and state code."""
    if not isinstance(gstin, str) or len(gstin) != 15:
        return False
    if not GSTIN_PATTERN.match(gstin):
        return False
    state_code = gstin[:2]
    return state_code in STATE_CODES

def validate_line_item(item: dict) -> None:
    """Validates individual line item numbers and rates."""
    if Decimal(str(item.get("quantity", 0))) <= 0:
        raise ValueError("Item quantity must be greater than 0")
    if Decimal(str(item.get("unit_price", 0))) < 0:
        raise ValueError("Item unit price cannot be negative")
    
    rate = Decimal(str(item.get("gst_rate", 0)))
    if rate not in VALID_GST_RATES:
        raise ValueError(f"Invalid GST rate: {rate}%. Allowed: {[float(r) for r in VALID_GST_RATES]}")

def validate_invoice_payload(payload: dict) -> None:
    """Validates top-level invoice payload."""
    if not payload.get("invoice_number"):
        raise ValueError("Invoice number is required")
    
    supplier_gstin = payload.get("supplier_gstin", "")
    if not validate_gstin(supplier_gstin):
        raise ValueError(f"Invalid supplier GSTIN: {supplier_gstin}")
    
    buyer_gstin = payload.get("buyer_gstin")
    if buyer_gstin and not validate_gstin(buyer_gstin):
        raise ValueError(f"Invalid buyer GSTIN: {buyer_gstin}")
        
    pos = payload.get("place_of_supply")
    if not pos or pos not in STATE_CODES:
        raise ValueError(f"Invalid or missing place of supply state code: {pos}")

    items = payload.get("items", [])
    if not items or len(items) == 0:
        raise ValueError("Invoice must contain at least one item")
    
    for item in items:
        validate_line_item(item)