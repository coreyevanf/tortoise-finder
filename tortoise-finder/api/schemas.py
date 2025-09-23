from pydantic import BaseModel
from typing import List, Optional

class RunRequest(BaseModel):
    dataset_uri: str
    model_version: str | None = "production"
    threshold: float = 0.8

class RunResponse(BaseModel):
    job_id: str
    run_id: str

class StatusResponse(BaseModel):
    state: str
    progress_pct: float
    eta_s: int | None = None

class PositiveItem(BaseModel):
    tile_id: str
    image_url: str
    thumb_url: str
    lat: float
    lon: float
    score: float

class Page(BaseModel):
    items: List[PositiveItem]
    total: int

class ConfirmRequest(BaseModel):
    run_id: str
    selections: List[dict]  # {tile_id:str, confirmed:bool}

class ExportFormat(str):
    pass  # 'geojson' | 'csv' | 'gpx' | 'kml'
