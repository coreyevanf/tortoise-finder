import os
import json
from fastapi import FastAPI, Query, Depends
from redis import Redis
from rq import Queue
from api.schemas import *
from api.deps import get_redis, get_queue
from storage.paths import results_key, geojson_key
from storage.io import get_url
from pipeline.run import run_inference_job
from pipeline.export import export_results
from pipeline.utils import read_results_table

app = FastAPI(title="tortoise-finder API")

@app.post("/run", response_model=RunResponse)
def run(req: RunRequest, queue: Queue = Depends(get_queue)):
    job = queue.enqueue(run_inference_job, req.dataset_uri, req.model_version, req.threshold)
    return RunResponse(job_id=job.id, run_id=job.id)

@app.get("/status/{job_id}", response_model=StatusResponse)
def status(job_id: str, redis: Redis = Depends(get_redis)):
    from rq.job import Job
    job = Job.fetch(job_id, connection=redis)
    meta = job.meta or {}
    state = job.get_status()
    return StatusResponse(state=state, progress_pct=meta.get("progress", 0), eta_s=meta.get("eta"))

@app.get("/positives", response_model=Page)
def positives(run_id: str, threshold: float = 0.8, page: int = 1, page_size: int = 40):
    df = read_results_table(run_id)
    df = df[df.score >= threshold]
    total = len(df)
    df = df.sort_values("score", ascending=False).iloc[(page-1)*page_size: page*page_size]
    items = []
    for _, r in df.iterrows():
        items.append(PositiveItem(
            tile_id=r.tile_id, image_url=r.image_url, thumb_url=r.thumb_url,
            lat=float(r.lat), lon=float(r.lon), score=float(r.score)
        ))
    return Page(items=items, total=total)

@app.post("/confirm")
def confirm(req: ConfirmRequest):
    # MVP: write confirmations into a sidecar JSON
    from storage.io import put_bytes
    key = f"runs/{req.run_id}/confirmations.json"
    data = json.dumps(req.model_dump(), indent=2).encode()
    from os import getenv
    put_bytes(getenv("ARTIFACT_BUCKET"), key, data, "application/json")
    return {"ok": True}

@app.get("/export")
def export(run_id: str, fmt: str = "geojson"):
    key = export_results(run_id, fmt)
    from os import getenv
    url = get_url(getenv("ARTIFACT_BUCKET"), key)
    return {"url": url}
