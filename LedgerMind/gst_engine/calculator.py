from decimal import Decimal, ROUND_HALF_UP
from gst_engine.validator import validate_invoice_payload

def round_inr(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def calculate_invoice(payload: dict) -> dict:
    validate_invoice_payload(payload)

    supplier_state = payload["supplier_gstin"][:2]
    place_of_supply = payload["place_of_supply"]
    is_intra_state = (supplier_state == place_of_supply)

    total_taxable = Decimal("0.00")
    total_cgst = Decimal("0.00")
    total_sgst = Decimal("0.00")
    total_igst = Decimal("0.00")

    calculated_items = []

    for item in payload["items"]:
        qty = Decimal(str(item["quantity"]))
        price = Decimal(str(item["unit_price"]))
        discount = Decimal(str(item.get("discount", 0)))
        rate = Decimal(str(item["gst_rate"]))

        taxable = round_inr((qty * price) - discount)
        if taxable < 0:
            taxable = Decimal("0.00")

        if is_intra_state:
            half_rate = rate / Decimal("2")
            cgst = round_inr((taxable * half_rate) / Decimal("100"))
            sgst = round_inr((taxable * half_rate) / Decimal("100"))
            igst = Decimal("0.00")
        else:
            cgst = Decimal("0.00")
            sgst = Decimal("0.00")
            igst = round_inr((taxable * rate) / Decimal("100"))

        item_total = taxable + cgst + sgst + igst

        total_taxable += taxable
        total_cgst += cgst
        total_sgst += sgst
        total_igst += igst

        calculated_items.append({
            "item_name": item.get("item_name", "Item"),
            "taxable_value": float(taxable),
            "gst_rate": float(rate),
            "cgst": float(cgst),
            "sgst": float(sgst),
            "igst": float(igst),
            "total": float(item_total)
        })

    grand_total = total_taxable + total_cgst + total_sgst + total_igst

    return {
        "invoice_number": payload["invoice_number"],
        "is_intra_state": is_intra_state,
        "total_taxable_value": float(total_taxable),
        "total_cgst": float(total_cgst),
        "total_sgst": float(total_sgst),
        "total_igst": float(total_igst),
        "total_tax": float(total_cgst + total_sgst + total_igst),
        "grand_total": float(grand_total),
        "items": calculated_items
    }