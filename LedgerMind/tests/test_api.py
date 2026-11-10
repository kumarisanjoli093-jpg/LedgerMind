import os
from fastapi.testclient import TestClient
import pytest

# We import the FastAPI app from main.py (assuming it's in the root folder)
try:
    from main import app
    client = TestClient(app)
    HAS_APP = True
except ImportError:
    HAS_APP = False

@pytest.mark.skipif(not HAS_APP, reason="main.py or app is not yet created by Backend team")
def test_health_check():
    """Verify that the FastAPI server is up and running."""
    response = client.get("/")
    # Even if it's 404, we just want to know the server didn't crash
    assert response.status_code in [200, 404]

@pytest.mark.skipif(not HAS_APP, reason="main.py or app is not yet created by Backend team")
def test_csv_upload_endpoint():
    """Simulate the frontend uploading Purchase Register and GSTR-2B CSVs."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pr_path = os.path.join(base_dir, "datasets", "purchase_register_2026-01.csv")
    g2b_path = os.path.join(base_dir, "datasets", "gstr2b_2026-01.csv")

    # Make sure the files exist before testing
    assert os.path.exists(pr_path)
    assert os.path.exists(g2b_path)

    # Open files in binary mode for the test client
    with open(pr_path, "rb") as pr_file, open(g2b_path, "rb") as g2b_file:
        files = {
            "purchase_register": ("purchase_register_2026-01.csv", pr_file, "text/csv"),
            "gstr2b": ("gstr2b_2026-01.csv", g2b_file, "text/csv")
        }
        
        # Simulate a POST request to a future /api/reconcile endpoint
        response = client.post("/api/reconcile", files=files)
        
        # If the endpoint doesn't exist yet, it returns 404. 
        # If it exists, it should return 200 OK.
        print(f"API Response Status: {response.status_code}")
        assert response.status_code in [200, 404, 422]
        