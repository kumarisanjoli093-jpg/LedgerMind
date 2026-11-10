import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

import main
import backend.db as db
import backend.api_transactions as at
from backend.schemas import TransactionCreate
import backend.api_chat as ac
import backend.stubs as stubs
import integrations


class TestDatabaseAndStartup(unittest.TestCase):
    def test_startup_initializes_both_databases(self):
        main.startup()
        # Verify gst_agent.db has purchase table
        conn = main.db()
        count = conn.execute("SELECT COUNT(*) FROM purchase").fetchone()[0]
        conn.close()
        self.assertGreater(count, 0)

        # Verify ledgermind.db has transactions table
        with db.get_connection() as c:
            cur = c.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
            table = cur.fetchone()
            self.assertIsNotNone(table)


class TestTransactionsAPI(unittest.TestCase):
    def setUp(self):
        db.init_db()

    def test_crud_lifecycle(self):
        tx_data = TransactionCreate(
            vendor="Unit Test Supplies",
            gstin="29ABCDE1234F1Z5",
            invoice_number="INV-TEST-001",
            invoice_date="2026-11-11",
            taxable_amount=2000.0,
            cgst=180.0,
            sgst=180.0,
            igst=0.0,
            total_tax=360.0,
            total_amount=2360.0,
            user_id=1
        )

        # 1. Create
        create_res = at.create_transaction(tx_data)
        self.assertIn("id", create_res)
        tx_id = create_res["id"]

        # 2. Read
        all_tx = at.get_transactions()
        found = next((t for t in all_tx if t["id"] == tx_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["vendor"], "Unit Test Supplies")

        # 3. Update
        tx_data.vendor = "Unit Test Supplies Updated"
        up_res = at.update_transaction(tx_id, tx_data)
        self.assertIn("message", up_res)

        # Verify update
        all_tx = at.get_transactions()
        updated_item = next(t for t in all_tx if t["id"] == tx_id)
        self.assertEqual(updated_item["vendor"], "Unit Test Supplies Updated")

        # 4. Delete
        del_res = at.delete_transaction(tx_id)
        self.assertIn("message", del_res)

        # Verify deletion
        all_tx = at.get_transactions()
        self.assertFalse(any(t["id"] == tx_id for t in all_tx))


class TestIntegrationsAndStatus(unittest.TestCase):
    def test_memory_status_contract(self):
        status = integrations.memory_status()
        self.assertIn("hindsight", status)
        self.assertIn("groq", status)
        self.assertIn("band_ai", status)
        self.assertIn("openclaw", status)

        self.assertIn("configured", status["hindsight"])
        self.assertIn("connected", status["hindsight"])
        self.assertIn("bank_id", status["hindsight"])


class TestChatAPI(unittest.TestCase):
    @patch("integrations.get_hindsight_client")
    def test_ask_ledgermind(self, mock_get_client):
        mock_result = MagicMock()
        mock_item = MagicMock()
        mock_item.text = "Vendor was nudged regarding missing credit."
        mock_result.results = [mock_item]

        client_instance = MagicMock()
        client_instance.recall.return_value = mock_result
        client_instance.retain.return_value = True
        mock_get_client.return_value = client_instance

        req = ac.ChatRequest(question="What is the vendor history?", user_id=1)
        res = ac.ask_ledgermind(req)

        self.assertEqual(res["question"], "What is the vendor history?")
        self.assertIn("answer", res)
        self.assertGreaterEqual(res["hindsight_memories_used"], 1)


class TestBackendStubs(unittest.TestCase):
    def test_calculate_gst(self):
        intra = stubs.calculate_gst(1000.0, 18.0, "KA", "KA")
        self.assertEqual(intra["cgst"], 90.0)
        self.assertEqual(intra["sgst"], 90.0)
        self.assertEqual(intra["igst"], 0.0)

        inter = stubs.calculate_gst(1000.0, 18.0, "KA", "DL")
        self.assertEqual(inter["cgst"], 0.0)
        self.assertEqual(inter["sgst"], 0.0)
        self.assertEqual(inter["igst"], 180.0)

    def test_validate_invoice(self):
        errors_valid = stubs.validate_invoice({"taxable": 100, "gstin": "29ABCDE1234F1Z5"})
        self.assertEqual(len(errors_valid), 0)

        errors_invalid = stubs.validate_invoice({"taxable": -10, "gstin": "short"})
        self.assertEqual(len(errors_invalid), 2)


if __name__ == "__main__":
    unittest.main()
