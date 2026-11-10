from backend.database import SessionLocal
from backend.models import Vendor

def seed_database():
    db = SessionLocal()
    print("Seeding database with master vendors...")

    # Master list of vendors matching our synthetic datasets
    vendors_data = [
        {"gstin": "27AABCS1429B1Z1", "name": "Sharma Traders", "risk_score": 85.0, "pref": "WhatsApp"},
        {"gstin": "29AABCA2233C1Z2", "name": "Apex Industrial Supplies", "risk_score": 60.0, "pref": "Email"},
        {"gstin": "07AABCN5566D1Z5", "name": "Nova Tech Solutions", "risk_score": 40.0, "pref": "Email"},
        {"gstin": "36AABCZ9988E1Z9", "name": "Zenith Logistics", "risk_score": 10.0, "pref": "Email"},
        {"gstin": "33AABCB1122F1Z4", "name": "BlueStar Enterprises", "risk_score": 5.0, "pref": "WhatsApp"},
    ]

    for v_data in vendors_data:
        # Check if vendor already exists to prevent duplicate errors
        existing = db.query(Vendor).filter(Vendor.gstin == v_data["gstin"]).first()
        if not existing:
            vendor = Vendor(
                gstin=v_data["gstin"],
                name=v_data["name"],
                risk_score=v_data["risk_score"],
                communication_preference=v_data["pref"]
            )
            db.add(vendor)
            print(f"Added vendor: {v_data['name']}")
        else:
            print(f"Vendor {v_data['name']} already exists. Skipping.")

    db.commit()
    db.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed_database()