#!/usr/bin/env python3
import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List, Tuple, Union


GeoJSON = dict
Coordinate = Tuple[float, float]


def read_text_file(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def write_text_file(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(data)


def fetch_fernandina_geojson(cache_path: Path, verbose: bool = True) -> GeoJSON:
    """Fetch Fernandina Island polygon GeoJSON via OSM Nominatim and cache it.

    If cache exists, load and return it.
    """
    if cache_path.exists():
        if verbose:
            print(f"Using cached polygon: {cache_path}")
        return json.loads(read_text_file(cache_path))

    # Nominatim terms require a valid UA and considerate usage.
    # We request a single object with polygon_geojson included.
    import urllib.parse
    import urllib.request

    query = {
        "q": "Fernandina Island, Galápagos, Ecuador",
        "format": "json",
        "limit": "1",
        "polygon_geojson": "1",
    }
    url = (
        "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(query)
    )
    if verbose:
        print(f"Fetching Fernandina polygon from: {url}")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "galapagos-tortoise-finder/1.0 (+contact: local script)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8")
    results = json.loads(data)
    if not results:
        raise RuntimeError("Nominatim returned no results for Fernandina Island")

    geojson = results[0].get("geojson")
    if not geojson:
        raise RuntimeError("No GeoJSON polygon found in Nominatim response")

    # Persist a minimal FeatureCollection for clarity and future re-use
    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "source": "nominatim",
                    "display_name": results[0].get("display_name"),
                },
                "geometry": geojson,
            }
        ],
    }
    write_text_file(cache_path, json.dumps(feature_collection))
    if verbose:
        print(f"Saved polygon to: {cache_path}")
    return feature_collection


def iter_all_rings(geometry: GeoJSON) -> Iterable[List[Coordinate]]:
    """Yield all polygon rings (outer and holes) as lists of (lon, lat).

    Handles Polygon and MultiPolygon GeoJSON geometries.
    """
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Polygon":
        for ring in coords:  # type: ignore[assignment]
            yield [(float(x), float(y)) for x, y in ring]
    elif gtype == "MultiPolygon":
        for poly in coords:  # type: ignore[assignment]
            for ring in poly:
                yield [(float(x), float(y)) for x, y in ring]
    else:
        raise ValueError(f"Unsupported geometry type: {gtype}")


def get_polygons(geometry: GeoJSON) -> List[List[List[Coordinate]]]:
    """Return list of polygons, each as [outer_ring, hole1, hole2, ...]."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    polygons: List[List[List[Coordinate]]] = []
    if gtype == "Polygon":
        poly: List[List[Coordinate]] = []
        for ring in coords:  # type: ignore[assignment]
            poly.append([(float(x), float(y)) for x, y in ring])
        polygons.append(poly)
    elif gtype == "MultiPolygon":
        for poly in coords:  # type: ignore[assignment]
            rings: List[List[Coordinate]] = []
            for ring in poly:
                rings.append([(float(x), float(y)) for x, y in ring])
            polygons.append(rings)
    else:
        raise ValueError(f"Unsupported geometry type: {gtype}")
    return polygons


def compute_bbox(geometry: GeoJSON) -> Tuple[float, float, float, float]:
    minx = float("inf")
    miny = float("inf")
    maxx = float("-inf")
    maxy = float("-inf")
    for ring in iter_all_rings(geometry):
        for x, y in ring:
            if x < minx:
                minx = x
            if y < miny:
                miny = y
            if x > maxx:
                maxx = x
            if y > maxy:
                maxy = y
    return minx, miny, maxx, maxy


def point_in_ring(point: Coordinate, ring: List[Coordinate]) -> bool:
    """Ray casting algorithm for a single ring. Assumes ring may be closed or open."""
    x, y = point
    inside = False
    n = len(ring)
    if n == 0:
        return False
    # Ensure we iterate over edges (xi, yi) -> (xj, yj)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        # Check if point is between yi and yj with respect to y
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def point_in_polygon(point: Coordinate, polygon: List[List[Coordinate]]) -> bool:
    """Return True if point is inside polygon (outer ring minus holes)."""
    if not polygon:
        return False
    outer = polygon[0]
    if not point_in_ring(point, outer):
        return False
    # Exclude holes
    for hole in polygon[1:]:
        if point_in_ring(point, hole):
            return False
    return True


def point_in_multipolygon(point: Coordinate, polygons: List[List[List[Coordinate]]]) -> bool:
    for poly in polygons:
        if point_in_polygon(point, poly):
            return True
    return False


def random_point_in_geometry(geometry: GeoJSON, max_attempts: int = 10000) -> Coordinate:
    polygons = get_polygons(geometry)
    minx, miny, maxx, maxy = compute_bbox(geometry)
    for _ in range(max_attempts):
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        if point_in_multipolygon((x, y), polygons):
            return (x, y)
    raise RuntimeError("Failed to sample point inside polygon after many attempts")


def find_images(folder: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".JPG", ".JPEG", ".PNG", ".TIF", ".TIFF", ".HEIC"}
    files: List[Path] = []
    for root, _dirs, filenames in os.walk(folder):
        for name in filenames:
            if Path(name).suffix in exts:
                files.append(Path(root) / name)
    files.sort()
    return files


def write_gps_with_exiftool(image_path: Path, lat: float, lon: float, quiet: bool = True) -> None:
    lat_ref = "N" if lat >= 0 else "S"
    lon_ref = "E" if lon >= 0 else "W"
    lat_abs = abs(lat)
    lon_abs = abs(lon)

    cmd = [
        "exiftool",
        "-overwrite_original_in_place",
        "-GPSLatitude={:.8f}".format(lat_abs),
        f"-GPSLatitudeRef={lat_ref}",
        "-GPSLongitude={:.8f}".format(lon_abs),
        f"-GPSLongitudeRef={lon_ref}",
        "-EXIF:GPSMapDatum=WGS-84",
        str(image_path),
    ]
    stdout_opt = subprocess.DEVNULL if quiet else None
    stderr_opt = subprocess.DEVNULL if quiet else None
    result = subprocess.run(cmd, stdout=stdout_opt, stderr=stderr_opt)
    if result.returncode != 0:
        raise RuntimeError(f"exiftool failed for {image_path}")


def main(argv: Union[List[str], None] = None) -> int:
    parser = argparse.ArgumentParser(description="Write random Fernandina Island GPS EXIF to images")
    parser.add_argument(
        "--folder",
        required=True,
        help="Target folder containing images",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional RNG seed for reproducibility",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of images processed",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print planned updates without writing EXIF",
    )
    args = parser.parse_args(argv)

    if args.seed is not None:
        random.seed(args.seed)
    else:
        random.seed(time.time_ns())

    folder = Path(args.folder).expanduser().resolve()
    if not folder.exists():
        print(f"Folder not found: {folder}", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parents[1]
    cache_path = repo_root / "tools" / "data" / "fernandina.geojson"

    feature_collection = fetch_fernandina_geojson(cache_path, verbose=True)
    # Expect one feature with Polygon or MultiPolygon
    features = feature_collection.get("features", [])
    if not features:
        print("No features in Fernandina GeoJSON", file=sys.stderr)
        return 1
    geometry = features[0].get("geometry")
    if not geometry:
        print("Feature has no geometry", file=sys.stderr)
        return 1

    images = find_images(folder)
    if args.limit is not None:
        images = images[: args.limit]
    if not images:
        print(f"No images found in {folder}")
        return 0

    print(f"Found {len(images)} images. Sampling points inside Fernandina Island polygon...")
    processed = 0
    for img in images:
        lon, lat = random_point_in_geometry(geometry)
        print(f"{img}: lat={lat:.6f}, lon={lon:.6f}")
        if not args.dry_run:
            write_gps_with_exiftool(img, lat=lat, lon=lon, quiet=True)
        processed += 1

    print(f"Done. Updated {processed} images.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


