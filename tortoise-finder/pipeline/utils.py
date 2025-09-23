import os
import tempfile
import pandas as pd
from storage.io import client
from storage.paths import results_key

BUCKET = os.environ["ARTIFACT_BUCKET"]

def read_results_table(run_id: str) -> pd.DataFrame:
    c = client()
    obj = c.get_object(BUCKET, results_key(run_id))
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        with open(tmp.name, "wb") as f: 
            f.write(obj.read())
        return pd.read_parquet(tmp.name)
