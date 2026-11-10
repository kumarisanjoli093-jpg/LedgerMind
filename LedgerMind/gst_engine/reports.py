from decimal import Decimal
from typing import List, Dict, Any

def generate_gst_summary_report(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates summary report for invoices:
    - Segregates B2B (registered buyer) vs B2C (unregistered buyer)
    - Aggregates rate-wise tax breakdowns
    """
    report = {
        "total_invoices_processed": len(invoices),
        "total_taxable_turnover": 0.0,
        "total_tax_collected": 0.0,
        "total_cgst": 0.0,
        "total_sgst": 0.0,
        "total_igst": 0.0,
        "b2b_invoices": [],
        "b2c_invoices": [],
        "rate_wise_summary": {
            0.0: {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0},
            5.0: {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0},
            12.0: {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0},
            18.0: {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0},
            28.0: {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0},
        }
    }

    tot_taxable = Decimal("0.00")
    tot_cgst = Decimal("0.00")
    tot_sgst = Decimal("0.00")
    tot_igst = Decimal("0.00")

    for inv in invoices:
        # B2B if buyer GSTIN present, else B2C
        inv_no = inv.get("invoice_number")
        if inv.get("buyer_gstin"):
            report["b2b_invoices"].append(inv_no)
        else:
            report["b2c_invoices"].append(inv_no)

        tot_taxable += Decimal(str(inv.get("total_taxable_value", 0.0)))
        tot_cgst += Decimal(str(inv.get("total_cgst", 0.0)))
        tot_sgst += Decimal(str(inv.get("total_sgst", 0.0)))
        tot_igst += Decimal(str(inv.get("total_igst", 0.0)))

        for item in inv.get("items", []):
            rate = float(item["gst_rate"])
            if rate in report["rate_wise_summary"]:
                report["rate_wise_summary"][rate]["taxable"] += float(item["taxable_value"])
                report["rate_wise_summary"][rate]["cgst"] += float(item["cgst"])
                report["rate_wise_summary"][rate]["sgst"] += float(item["sgst"])
                report["rate_wise_summary"][rate]["igst"] += float(item["igst"])

    report["total_taxable_turnover"] = float(tot_taxable)
    report["total_cgst"] = float(tot_cgst)
    report["total_sgst"] = float(tot_sgst)
    report["total_igst"] = float(tot_igst)
    report["total_tax_collected"] = float(tot_cgst + tot_sgst + tot_igst)

    return report