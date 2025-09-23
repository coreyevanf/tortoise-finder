import os
import tempfile
import json
import pandas as pd
# import geopandas as gpd  # Temporarily disabled
# from shapely.geometry import Point  # Temporarily disabled
from storage.io import put_file
from storage.paths import geojson_key

BUCKET = os.environ["ARTIFACT_BUCKET"]

def _df(run_id: str) -> pd.DataFrame:
    from .utils import read_results_table
    return read_results_table(run_id)

def export_results(run_id: str, fmt: str = "geojson") -> str:
    df = _df(run_id)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}") as tmp:
        if fmt == "geojson":
            # Create simple GeoJSON without geopandas
            geojson = {
                "type": "FeatureCollection",
                "features": []
            }
            for _, row in df.iterrows():
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(row.lon), float(row.lat)]
                    },
                    "properties": {
                        "tile_id": row.tile_id,
                        "score": float(row.score)
                    }
                }
                geojson["features"].append(feature)
            
            with open(tmp.name, 'w') as f:
                json.dump(geojson, f, indent=2)
            key = geojson_key(run_id)
        elif fmt == "csv":
            df[["lat", "lon", "score", "tile_id"]].to_csv(tmp.name, index=False)
            key = f"runs/{run_id}/positives.csv"
        elif fmt == "gpx":
            # Simple GPX export without geopandas
            gpx_content = '<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1">\n'
            for _, row in df.iterrows():
                gpx_content += f'  <wpt lat="{row.lat}" lon="{row.lon}">\n'
                gpx_content += f'    <name>{row.tile_id}</name>\n'
                gpx_content += f'    <desc>Score: {row.score}</desc>\n'
                gpx_content += '  </wpt>\n'
            gpx_content += '</gpx>'
            with open(tmp.name, 'w') as f:
                f.write(gpx_content)
            key = f"runs/{run_id}/positives.gpx"
        elif fmt == "kml":
            # Simple KML export without geopandas
            kml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
            for _, row in df.iterrows():
                kml_content += f'  <Placemark>\n'
                kml_content += f'    <name>{row.tile_id}</name>\n'
                kml_content += f'    <description>Score: {row.score}</description>\n'
                kml_content += f'    <Point><coordinates>{row.lon},{row.lat},0</coordinates></Point>\n'
                kml_content += f'  </Placemark>\n'
            kml_content += '</Document>\n</kml>'
            with open(tmp.name, 'w') as f:
                f.write(kml_content)
            key = f"runs/{run_id}/positives.kml"
        else:
            raise ValueError("unsupported format")
        put_file(BUCKET, key, tmp.name)
        return key
