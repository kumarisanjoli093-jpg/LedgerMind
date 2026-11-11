
import json
from typing import Optional

from google.genai import types
from pydantic import ValidationError

from .gemini_client import get_gemini_client, get_model_name
from .schemas import InvoiceExtraction


EXTRACTION_PROMPT = """
You are LedgerMind, an AI-powered Indian GST invoice extraction engine.

Extract information from the supplied invoice or receipt.

Return accurate structured information using the provided schema.

IMPORTANT RULES:

1. Never invent missing information.
2. Use null for unavailable or unreadable fields.
3. Extract the supplier and buyer GSTIN exactly as printed.
4. Extract invoice number and invoice date exactly.
5. Identify CGST, SGST, IGST and cess separately.
6. Extract every visible line item.
7. Preserve HSN/SAC codes.
8. Convert monetary amounts and quantities into numbers.
9. Use INR as the default currency when appropriate.
10. Set confidence between 0 and 1 based on extraction quality.
11. Add warnings for missing, ambiguous or unreadable information.
12. Do not assume that a document is a valid GST invoice merely
    because it contains tax-related information.

For document_type, use an appropriate value such as:
tax_invoice, bill_of_supply, credit_note, debit_note,
receipt, or unknown.

Return only structured data matching the supplied schema.
"""


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


def extract_invoice(
    file_bytes: bytes,
    mime_type: str,
    document_name: Optional[str] = None,
) -> InvoiceExtraction:
    """
    Extract structured invoice information from a PDF or image.

    Args:
        file_bytes: Raw document bytes.
        mime_type: Document MIME type.
        document_name: Optional original filename.

    Returns:
        Validated InvoiceExtraction object.

    Raises:
        ValueError: Invalid or unsupported document.
        RuntimeError: Gemini or extraction failure.
    """

    if not file_bytes:
        raise ValueError("The uploaded document is empty.")

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(
            f"Unsupported document type: {mime_type}"
        )

    prompt = EXTRACTION_PROMPT

    if document_name:
        prompt += f"\nDocument name: {document_name}"

    try:
        client = get_gemini_client()

        document_part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type,
        )

        response = client.models.generate_content(
            model=get_model_name(),
            contents=[
                prompt,
                document_part,
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=InvoiceExtraction,
            ),
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty extraction response."
            )

        extracted_data = json.loads(response.text)

        result = InvoiceExtraction.model_validate(
            extracted_data
        )

        return result

    except ValidationError as exc:
        raise RuntimeError(
            f"Invoice data validation failed: {exc}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini returned invalid JSON."
        ) from exc

    except RuntimeError:
        raise

    except Exception as exc:
        raise RuntimeError(
            f"Invoice extraction failed: {exc}"
        ) from exc

