
import os
import pytest

from ai_agent.invoice_extractor import extract_invoice


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Gemini API key not configured",
)
def test_real_invoice_extraction():

    # Minimal PDF containing sample invoice information.
    pdf_content = b"""%PDF-1.1
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Resources << /Font << /F1 4 0 R >> >>
/Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 250 >>
stream
BT
/F1 12 Tf
50 750 Td
(ABC TRADERS) Tj
0 -25 Td
(TAX INVOICE) Tj
0 -25 Td
(Invoice Number: INV-TEST-001) Tj
0 -25 Td
(Date: 11-11-2026) Tj
0 -25 Td
(GSTIN: 29ABCDE1234F1Z5) Tj
0 -25 Td
(Total: Rs 1180) Tj
ET
endstream
endobj
6 0 obj
<< /Type /XRef /Size 7 /Root 1 0 R /Length 0 >>
stream
endstream
endobj
trailer
<< /Root 1 0 R /Size 7 >>
startxref
0
%%EOF
"""

    result = extract_invoice(
        file_bytes=pdf_content,
        mime_type="application/pdf",
        document_name="sample_invoice.pdf",
    )

    assert result is not None
    assert result.document_type in [
        "tax_invoice",
        "unknown",
    ]
    assert result.confidence >= 0
    assert result.confidence <= 1
    assert isinstance(result.line_items, list)

