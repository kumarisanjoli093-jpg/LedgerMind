
import hashlib
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .agent import ask_ledger_mind
from .invoice_extractor import extract_invoice
from .rag import rag_engine
from .schemas import AskRequest


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ai",
    tags=["LedgerMind AI Agent"]
)

MAX_UPLOAD_SIZE = 15 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


class IngestTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200000)
    source: str = Field(default="team-document", max_length=200)
    vendor: str | None = Field(default=None, max_length=200)


# --------------------------------------------------
# 1. INVOICE EXTRACTION
# --------------------------------------------------

@router.post("/extract-invoice")
async def extract_invoice_route(
    file: UploadFile = File(...)
):
    """
    Upload an invoice or receipt and extract
    structured financial information using Gemini.
    """

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Upload a PDF, JPG, PNG or WEBP document."
        )

    try:
        file_bytes = await file.read(MAX_UPLOAD_SIZE + 1)

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded document is empty."
            )

        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Maximum document size is 15 MB."
            )

        invoice = extract_invoice(
            file_bytes=file_bytes,
            mime_type=file.content_type,
            document_name=file.filename,
        )

        invoice_data = invoice.model_dump(mode="json")

        # Store extracted invoice data in the RAG knowledge base.
        document_id = hashlib.sha256(
            file_bytes
        ).hexdigest()

        chunks_added = rag_engine.add_document(
            document_id=document_id,
            text=invoice.model_dump_json(indent=2),
            metadata={
                "filename": file.filename or "uploaded-invoice",
                "vendor": invoice.supplier_name or "",
                "supplier_gstin": invoice.supplier_gstin or "",
                "document_type": invoice.document_type,
                "invoice_number": invoice.invoice_number or "",
            }
        )

        return {
            "success": True,
            "message": "Invoice extracted and stored successfully.",
            "document_id": document_id,
            "invoice": invoice_data,
            "rag_chunks_added": chunks_added,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        logger.exception("Invoice extraction endpoint failed.")

        raise HTTPException(
            status_code=502,
            detail="Invoice processing failed. Check server logs."
        ) from exc

    finally:
        await file.close()


# --------------------------------------------------
# 2. AI FINANCIAL QUESTION ANSWERING
# --------------------------------------------------

@router.post("/ask")
def ask_financial_question(
    request: AskRequest
):
    """
    Ask LedgerMind questions about stored
    invoices and historical financial records.
    """

    try:
        result = ask_ledger_mind(
            question=request.question,
            vendor=request.vendor,
            top_k=request.top_k,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        logger.exception("AI question answering failed.")

        raise HTTPException(
            status_code=502,
            detail="LedgerMind could not answer the question."
        ) from exc


# --------------------------------------------------
# 3. DOCUMENT INGESTION
# --------------------------------------------------

@router.post("/ingest-text")
def ingest_text_document(
    request: IngestTextRequest
):
    """
    Add financial reference information
    directly to the RAG knowledge base.
    """

    document_id = hashlib.sha256(
        f"{request.source}:{request.text}".encode("utf-8")
    ).hexdigest()

    metadata = {
        "source": request.source,
        "vendor": request.vendor or "",
        "document_type": "reference_document",
    }

    try:
        chunks_added = rag_engine.add_document(
            document_id=document_id,
            text=request.text,
            metadata=metadata,
        )

        return {
            "success": True,
            "message": "Document added to knowledge base.",
            "document_id": document_id,
            "chunks_added": chunks_added,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        logger.exception("Document ingestion failed.")

        raise HTTPException(
            status_code=502,
            detail="Document ingestion failed."
        ) from exc

