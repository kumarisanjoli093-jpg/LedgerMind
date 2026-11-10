import pytest
from gst_engine.calculator import calculate_invoice
from gst_engine.reports import generate_gst_summary_report

def test_intra_state_split():
    # Maharashtra (27) -> Maharashtra (27): 18% split into 9% CGST + 9% SGST
    invoice = {
        "invoice_number": "INV-001",
        "supplier_gstin": "27AAPFU0939F1ZV",
        "place_of_supply": "27",
        "items": [
            {"item_name": "Laptop", "quantity": 1, "unit_price": 1000, "gst_rate": 18, "discount": 0}
        ]
    }
    result = calculate_invoice(invoice)
    assert result["is_intra_state"] is True
    assert result["total_cgst"] == 90.0
    assert result["total_sgst"] == 90.0
    assert result["total_igst"] == 0.0
    assert result["grand_total"] == 1180.0

def test_inter_state_igst():
    # Maharashtra (27) -> Karnataka (29): Full 18% IGST
    invoice = {
        "invoice_number": "INV-002",
        "supplier_gstin": "27AAPFU0939F1ZV",
        "place_of_supply": "29",
        "items": [
            {"item_name": "Keyboard", "quantity": 2, "unit_price": 500, "gst_rate": 18, "discount": 100}
        ]
    }
    result = calculate_invoice(invoice)
    assert result["is_intra_state"] is False
    assert result["total_taxable_value"] == 900.0
    assert result["total_cgst"] == 0.0
    assert result["total_sgst"] == 0.0
    assert result["total_igst"] == 162.0
    assert result["grand_total"] == 1062.0

def test_zero_rate_gst():
    # 0% GST (exempt/essential goods)
    invoice = {
        "invoice_number": "INV-003",
        "supplier_gstin": "27AAPFU0939F1ZV",
        "place_of_supply": "27",
        "items": [
            {"item_name": "Milk", "quantity": 10, "unit_price": 30, "gst_rate": 0, "discount": 0}
        ]
    }
    result = calculate_invoice(invoice)
    assert result["total_tax"] == 0.0
    assert result["grand_total"] == 300.0

def test_invalid_gstin_fails():
    # Invalid supplier GSTIN must raise ValueError
    invoice = {
        "invoice_number": "INV-004",
        "supplier_gstin": "INVALID123",
        "place_of_supply": "27",
        "items": [
            {"item_name": "Item", "quantity": 1, "unit_price": 100, "gst_rate": 18}
        ]
    }
    with pytest.raises(ValueError, match="Invalid supplier GSTIN"):
        calculate_invoice(invoice)

def test_invalid_rate_fails():
    # Non-standard GST rate (e.g. 7%) must raise ValueError
    invoice = {
        "invoice_number": "INV-005",
        "supplier_gstin": "27AAPFU0939F1ZV",
        "place_of_supply": "27",
        "items": [
            {"item_name": "Item", "quantity": 1, "unit_price": 100, "gst_rate": 7}
        ]
    }
    with pytest.raises(ValueError, match="Invalid GST rate"):
        calculate_invoice(invoice)

def test_gst_report_generation():
    inv1 = calculate_invoice({
        "invoice_number": "INV-B2B",
        "supplier_gstin": "27AAPFU0939F1ZV",
        "buyer_gstin": "29AAPFU0939F1ZV",
        "place_of_supply": "29",
        "items": [{"item_name": "Item A", "quantity": 1, "unit_price": 1000, "gst_rate": 18, "discount": 0}]
    })
    inv1["buyer_gstin"] = "29AAPFU0939F1ZV"

    inv2 = calculate_invoice({
        "invoice_number": "INV-B2C",
        "supplier_gstin": "27AAPFU0939F1ZV",
        "place_of_supply": "27",
        "items": [{"item_name": "Item B", "quantity": 1, "unit_price": 500, "gst_rate": 5, "discount": 0}]
    })

    report = generate_gst_summary_report([inv1, inv2])
    assert report["total_invoices_processed"] == 2
    assert "INV-B2B" in report["b2b_invoices"]
    assert "INV-B2C" in report["b2c_invoices"]
    assert report["total_taxable_turnover"] == 1500.0
    assert report["total_tax_collected"] == 205.0  # 180 (IGST) + 25 (CGST+SGST)