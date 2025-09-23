import os
import uuid
import time
import random
import io
import pandas as pd
from PIL import Image, ImageOps
from storage.io import put_bytes, get_url
from storage.paths import results_key, thumbs_prefix
from rq import get_current_job

BUCKET = os.environ["ARTIFACT_BUCKET"]

def _update(progress):
    job = get_current_job()
    if job:
        job.meta["progress"] = progress
        job.save_meta()

def run_inference_job(dataset_uri: str, model_version: str | None, threshold: float):
    # MVP: synthesize 500 tiles with lat/lon around a fixed AOI
    n = 500
    rows = []
    for i in range(n):
        score = random.random()  # stand-in for real model score
        lat = -0.5 + random.random() * 0.5
        lon = -90.5 + random.random() * 0.5
        # create thumbnail
        img = ImageOps.colorize(Image.new("L", (128, 128), int(score * 255)), black="black", white="white")
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        b = buf.getvalue()
        tile_id = f"tile-{i:05d}"
        thumb_key = f"{thumbs_prefix(get_current_job().id)}/{tile_id}.webp"
        put_bytes(BUCKET, thumb_key, b, "image/webp")
        rows.append({
            "tile_id": tile_id, "score": score, "lat": lat, "lon": lon,
            "thumb_url": get_url(BUCKET, thumb_key), "image_url": get_url(BUCKET, thumb_key),
            "model_ver": model_version, "run_id": get_current_job().id
        })
        if i % 25 == 0: 
            _update(round(i / n * 100, 1))
    df = pd.DataFrame(rows)
    # store results parquet
    import pyarrow as pa
    import pyarrow.parquet as pq
    table = pa.Table.from_pandas(df)
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(suffix=".parquet") as tmp:
        pq.write_table(table, tmp.name)
        from storage.io import put_file
        put_file(BUCKET, results_key(get_current_job().id), tmp.name, "application/octet-stream")
    _update(100.0)
    return {"run_id": get_current_job().id, "n": len(df)}
