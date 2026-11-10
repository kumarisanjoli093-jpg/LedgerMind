import csv
import os
import uuid
import pytest
from backend.database import Base, SessionLocal, engine
from backend.models import Invoice, Mismatch, Vendor


@pytest.fixture(scope="module")
def db_session():
  Base.metadata.create_all(bind=engine)
  session = SessionLocal()
  yield session
  session.close()


def test_vendor_and_mismatch_creation(db_session):
  """Verify that a vendor and associated mismatch can be stored and linked."""
  # Use a dynamic GSTIN so repeated test runs never collide on the UNIQUE constraint
  unique_gstin = f"27{uuid.uuid4().hex[:10].upper()}Z1"

  # 1. Create a test vendor
  test_vendor = Vendor(
      gstin=unique_gstin,
      name="Test Vendor Pvt Ltd",
      risk_score=15.0,
      communication_preference="WhatsApp",
  )
  db_session.add(test_vendor)
  db_session.commit()
  db_session.refresh(test_vendor)

  assert test_vendor.id is not None
  assert test_vendor.name == "Test Vendor Pvt Ltd"

  # 2. Create a test mismatch linked to the vendor
  test_mismatch = Mismatch(
      vendor_id=test_vendor.id,
      filing_period="2026-01",
      category="TAX_MISMATCH",
      expected_value="1800.00",
      actual_value="1300.00",
      itc_at_risk=500.00,
      recommended_action="Notify vendor to file amendment in GSTR-1.",
      resolution_status="PENDING",
  )
  db_session.add(test_mismatch)
  db_session.commit()
  db_session.refresh(test_mismatch)

  assert test_mismatch.id is not None
  assert test_mismatch.vendor.name == "Test Vendor Pvt Ltd"
  assert test_mismatch.itc_at_risk == 500.00

  # Clean up test rows so the database stays tidy
  db_session.delete(test_mismatch)
  db_session.delete(test_vendor)
  db_session.commit()


def test_synthetic_datasets_exist():
  """Verify that dataset generation created the expected CSV files."""
  base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  datasets_dir = os.path.join(base_dir, "datasets")

  months = ["2026-01", "2026-02", "2026-03"]
  for m in months:
    pr_path = os.path.join(datasets_dir, f"purchase_register_{m}.csv")
    g2b_path = os.path.join(datasets_dir, f"gstr2b_{m}.csv")

    assert os.path.exists(pr_path), f"Missing Purchase Register for {m}"
    assert os.path.exists(g2b_path), f"Missing GSTR-2B for {m}"


def test_reconciliation_detects_missing_invoice():
  """Verify that a missing invoice in GSTR-2B is flagged (planted Sharma Traders case)."""
  base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  pr_path = os.path.join(base_dir, "datasets", "purchase_register_2026-01.csv")
  g2b_path = os.path.join(base_dir, "datasets", "gstr2b_2026-01.csv")

  with open(pr_path, mode="r", encoding="utf-8") as f:
    pr_rows = list(csv.DictReader(f))

  with open(g2b_path, mode="r", encoding="utf-8") as f:
    g2b_rows = list(csv.DictReader(f))

  pr_invs = {row["Invoice Number"]: row for row in pr_rows}
  g2b_invs = {row["Invoice Number"] for row in g2b_rows}

  missing = [inv_num for inv_num in pr_invs.keys() if inv_num not in g2b_invs]

  assert len(missing) >= 1
  missing_inv = pr_invs[missing[0]]
  assert missing_inv["Vendor Name"] == "Sharma Traders"
  assert float(missing_inv["Total Tax"]) > 0