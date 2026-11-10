from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    gstin = Column(String(15), unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    risk_score = Column(Float, default=0.0)
    communication_preference = Column(String, default="Email")  # 'WhatsApp', 'Email'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="vendor")
    mismatches = relationship("Mismatch", back_populates="vendor")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    invoice_number = Column(String, index=True, nullable=False)
    invoice_date = Column(String, nullable=False)  # Format: YYYY-MM-DD
    filing_period = Column(String, nullable=False)  # e.g., '2026-01'

    # Source Type: 'PURCHASE_REGISTER' or 'GSTR_2B'
    source_type = Column(String, nullable=False)

    taxable_value = Column(Float, default=0.0)
    igst = Column(Float, default=0.0)
    cgst = Column(Float, default=0.0)
    sgst = Column(Float, default=0.0)
    total_tax = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="invoices")
    mismatch = relationship("Mismatch", back_populates="invoice", uselist=False)


class Mismatch(Base):
    __tablename__ = "mismatches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    filing_period = Column(String, nullable=False)  # e.g., '2026-01'
    category = Column(String, nullable=False)  # 'MISSING_INVOICE', 'WRONG_GSTIN', etc.

    expected_value = Column(Text, nullable=True)  # Purchase Register value
    actual_value = Column(Text, nullable=True)    # GSTR-2B value

    itc_at_risk = Column(Float, default=0.0)
    recommended_action = Column(Text, nullable=True)
    resolution_status = Column(String, default="PENDING")  # 'PENDING', 'RESOLVED'

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="mismatches")
    invoice = relationship("Invoice", back_populates="mismatch")