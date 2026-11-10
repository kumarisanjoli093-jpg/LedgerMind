
from typing import Optional
from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    description: Optional[str] = None
    hsn_sac: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    taxable_value: Optional[float] = None
    tax_rate_percent: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None


class InvoiceExtraction(BaseModel):
    document_type: str = "unknown"

    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None

    supplier_name: Optional[str] = None
    supplier_gstin: Optional[str] = None

    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None

    place_of_supply: Optional[str] = None
    currency: str = "INR"

    taxable_value: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    cess: Optional[float] = None

    total_tax: Optional[float] = None
    grand_total: Optional[float] = None

    line_items: list[InvoiceLineItem] = Field(default_factory=list)

    confidence: float = Field(default=0, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    vendor: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=10)

