import csv
import os
import random

DATASETS_DIR = os.path.dirname(os.path.abspath(__file__))

VENDORS = [
    {
        "name": "Sharma Traders",
        "gstin": "27AABCS1429B1Z1",
        "pattern": "LATE_FILER",
        "pref": "WhatsApp",
    },
    {
        "name": "Apex Industrial Supplies",
        "gstin": "29AABCA2233C1Z2",
        "pattern": "GSTIN_ERROR",
        "pref": "Email",
    },
    {
        "name": "Nova Tech Solutions",
        "gstin": "07AABCN5566D1Z5",
        "pattern": "TAX_MISMATCH",
        "pref": "Email",
    },
    {
        "name": "Zenith Logistics",
        "gstin": "36AABCZ9988E1Z9",
        "pattern": "NORMAL",
        "pref": "Email",
    },
    {
        "name": "BlueStar Enterprises",
        "gstin": "33AABCB1122F1Z4",
        "pattern": "NORMAL",
        "pref": "WhatsApp",
    },
]

MONTHS = ["2026-01", "2026-02", "2026-03"]


def generate_data():
  print("Generating synthetic datasets...")

  for month in MONTHS:
    purchase_rows = []
    gstr2b_rows = []

    for v in VENDORS:
      inv_num = f"INV-{month.replace('-', '')}-{random.randint(100, 999)}"
      inv_date = f"{month}-10"
      taxable = round(random.uniform(25000, 150000), 2)
      tax_rate = 0.18
      cgst = round((taxable * tax_rate) / 2, 2)
      sgst = cgst
      igst = 0.0
      total_tax = round(cgst + sgst, 2)

      # 1. Purchase Register entry (baseline)
      purchase_rows.append({
          "Vendor Name": v["name"],
          "GSTIN": v["gstin"],
          "Invoice Number": inv_num,
          "Invoice Date": inv_date,
          "Filing Period": month,
          "Taxable Value": taxable,
          "CGST": cgst,
          "SGST": sgst,
          "IGST": igst,
          "Total Tax": total_tax,
      })

      # 2. GSTR-2B entry with planted patterns
      if v["pattern"] == "LATE_FILER" and month == "2026-01":
        # Supplier missed filing in January (missing from GSTR-2B)
        continue

      gstr_row = {
          "Vendor Name": v["name"],
          "GSTIN": v["gstin"],
          "Invoice Number": inv_num,
          "Invoice Date": inv_date,
          "Filing Period": month,
          "Taxable Value": taxable,
          "CGST": cgst,
          "SGST": sgst,
          "IGST": igst,
          "Total Tax": total_tax,
      }

      if v["pattern"] == "GSTIN_ERROR":
        # Typo planted in the GSTIN portal record
        gstr_row["GSTIN"] = v["gstin"][:-2] + "X9"

      elif v["pattern"] == "TAX_MISMATCH":
        # Mismatched tax figure
        gstr_row["CGST"] = round(cgst - 500, 2)
        gstr_row["SGST"] = round(sgst - 500, 2)
        gstr_row["Total Tax"] = round(total_tax - 1000, 2)

      gstr2b_rows.append(gstr_row)

    # Save to CSV files
    pr_file = os.path.join(DATASETS_DIR, f"purchase_register_{month}.csv")
    g2b_file = os.path.join(DATASETS_DIR, f"gstr2b_{month}.csv")

    fieldnames = [
        "Vendor Name",
        "GSTIN",
        "Invoice Number",
        "Invoice Date",
        "Filing Period",
        "Taxable Value",
        "CGST",
        "SGST",
        "IGST",
        "Total Tax",
    ]

    with open(pr_file, "w", newline="", encoding="utf-8") as f:
      writer = csv.DictWriter(f, fieldnames=fieldnames)
      writer.writeheader()
      writer.writerows(purchase_rows)

    with open(g2b_file, "w", newline="", encoding="utf-8") as f:
      writer = csv.DictWriter(f, fieldnames=fieldnames)
      writer.writeheader()
      writer.writerows(gstr2b_rows)

    print(f"Created: purchase_register_{month}.csv and gstr2b_{month}.csv")

  print("All synthetic datasets generated successfully!")


if __name__ == "__main__":
  generate_data()