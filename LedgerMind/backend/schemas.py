# backend/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class TransactionBase(BaseModel):
    vendor: str
    gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    taxable_amount: float = Field(..., ge=0)
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    total_tax: float = Field(..., ge=0)
    total_amount: float = Field(..., ge=0)

class TransactionCreate(TransactionBase):
    user_id: Optional[int] = 1 # Hardcoded for now until auth is added
    receipt_id: Optional[int] = None