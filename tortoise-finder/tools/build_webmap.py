#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


def run_exiftool_json(folder: Path) -> List[Dict]:
    cmd = [
        "exiftool",
        "-n",
        "-r",
        "-json",
        "-GPSLatitude",
        "-GPSLongitude",
        "-FileName",
        "-FileModifyDate",
        "-FileSize",
        str(folder),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"exiftool failed: {proc.stderr}")
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse exiftool JSON: {e}\n{proc.stdout[:500]}...")
    return data


def to_features(items: List[Dict], image_root: Path, webmap_dir: Path) -> List[Dict]:
    features: List[Dict] = []
    for it in items:
        lat = it.get("GPSLatitude")
        lon = it.get("GPSLongitude")
        src = it.get("SourceFile") or it.get("FileName")
        if lat is None or lon is None or not src:
            continue
        src_path = Path(src)
        # Compute relative path from webmap_dir to the image file
        try:
            rel = os.path.relpath(src_path, start=webmap_dir)
        except ValueError:
            # Different drive or other OS-specific issues; fall back to absolute
            rel = str(src_path)
        features.append({
            "type": "Feature",
            "properties": {
                "name": os.path.basename(src_path),
                "image": rel,
                "lat": lat,
                "lon": lon,
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })
    return features


def build_html(features: List[Dict], out_dir: Path, title: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"

    # Minimal Leaflet HTML with OSM + Esri World Imagery baselayers
    features_json = json.dumps({"type": "FeatureCollection", "features": features})
    template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>%%TITLE%%</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<style>
  html, body, #map { height: 100%; margin: 0; }
  .popup-img { max-width: 420px; height: auto; display: block; }
  .coords { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
const fc = %%FEATURES%%;
const map = L.map('map');
// Base layers
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' });
const esri = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19, attribution: 'Tiles &copy; Esri' });
const baseLayers = { 'OSM': osm, 'Satellite': esri };
// Markers
const markers = [];
const geo = L.geoJSON(fc, {
        pointToLayer: function(feature, latlng) {
            return L.marker(latlng);
        },
        onEachFeature: function(feature, layer) {
            const p = feature.properties || {};
            const img = p.image;
            const lat = p.lat;
            const lon = p.lon;
            const name = p.name || 'image';
            const popupHtml = `
                <div>
                  <div><strong>${name}</strong></div>
                  <div class="coords">Lat: ${lat.toFixed(6)}, Lon: ${lon.toFixed(6)}</div>
                  <div style="margin:6px 0;"><a href="${img}" target="_blank" rel="noopener">Open full image</a></div>
                  <img class="popup-img" src="${img}" alt="${name}"/>
                </div>
            `;
            layer.bindPopup(popupHtml);
            layer.bindTooltip(name, {direction: 'top'});
            markers.push(layer);
        }
    });
geo.addTo(map);
// Fit map to markers or set default view
if (markers.length > 0) {
    const group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.2));
} else {
    map.setView([0, -91.6], 10);
}
osm.addTo(map);
L.control.layers(baseLayers).addTo(map);
</script>
</body>
</html>"""
    html = template.replace("%%TITLE%%", title).replace("%%FEATURES%%", features_json)

    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Leaflet webmap of images with EXIF GPS")
    parser.add_argument("--folder", required=True, help="Folder containing images")
    parser.add_argument("--out", default=None, help="Output directory for webmap (default: webmap)")
    parser.add_argument("--title", default="Image Map", help="Page title")
    args = parser.parse_args()

    image_root = Path(args.folder).expanduser().resolve()
    if not image_root.exists():
        raise SystemExit(f"Folder not found: {image_root}")

    repo_root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out).expanduser().resolve() if args.out else (repo_root / "webmap")

    data = run_exiftool_json(image_root)
    features = to_features(data, image_root=image_root, webmap_dir=out_dir)
    if not features:
        print("No images with GPS EXIF found.")
    out_path = build_html(features, out_dir, args.title)
    print(f"Wrote webmap: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


