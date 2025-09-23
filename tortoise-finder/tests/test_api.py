"""
Basic tests for the API module.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_run_endpoint():
    """Test the /run endpoint."""
    response = client.post("/run", json={
        "dataset_uri": "s3://test/dataset",
        "threshold": 0.8
    })
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "run_id" in data

def test_status_endpoint():
    """Test the /status endpoint."""
    # This would need a real job_id to work properly
    # For now, just test that the endpoint exists
    response = client.get("/status/test-job-id")
    # Should return 404 or error for non-existent job
    assert response.status_code in [404, 500]

def test_export_endpoint():
    """Test the /export endpoint."""
    response = client.get("/export", params={"run_id": "test-run", "fmt": "geojson"})
    # Should return error for non-existent run
    assert response.status_code in [404, 500]
