import typer
import requests
import os
import json

app = typer.Typer()
API = os.environ.get("API_URL", "http://localhost:8000")

@app.command()
def run(dataset: str, threshold: float = 0.8):
    """Start a new inference run with the specified dataset."""
    r = requests.post(f"{API}/run", json={"dataset_uri": dataset, "threshold": threshold})
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))

@app.command()
def status(job_id: str):
    """Check the status of a running job."""
    r = requests.get(f"{API}/status/{job_id}")
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))

@app.command()
def export(run_id: str, fmt: str = "geojson"):
    """Export results from a completed run."""
    r = requests.get(f"{API}/export", params={"run_id": run_id, "fmt": fmt})
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))

@app.command()
def positives(run_id: str, threshold: float = 0.8, page: int = 1, page_size: int = 40):
    """List positive detections from a run."""
    r = requests.get(f"{API}/positives", params={"run_id": run_id, "threshold": threshold, "page": page, "page_size": page_size})
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    app()
