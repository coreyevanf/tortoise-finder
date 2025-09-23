#!/usr/bin/env python3
"""
Dead simple HTTP server demo for tortoise-finder.
No dependencies except Python standard library.
"""

import http.server
import socketserver
import json
import random
import urllib.parse
import os
import glob
import shutil
from datetime import datetime

# Try to import PIL for EXIF processing, fallback gracefully
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL/Pillow not available. EXIF GPS extraction disabled.")

# Dataset configuration
POSITIVE_PATH = "/Users/corey/galapagos/tortoise-finder/data/outputs/positive"
CONFIRMED_PATH = "/Users/corey/galapagos/tortoise-finder/data/outputs/confirmed"
NEGATIVE_PATH = "/Users/corey/galapagos/tortoise-finder/data/outputs/negative"

def get_local_images(dataset_path, limit=50):
    """Get list of local training images with metadata."""
    if not os.path.exists(dataset_path):
        return []
    
    image_files = glob.glob(os.path.join(dataset_path, "*.jpg"))[:limit]
    image_files += glob.glob(os.path.join(dataset_path, "*.jpeg"))[:limit]
    image_files += glob.glob(os.path.join(dataset_path, "*.png"))[:limit]
    results = []
    
    for i, image_path in enumerate(image_files):
        filename = os.path.basename(image_path)
        # Extract info from filename: B002T-20200709-165419_jpg.rf...
        parts = filename.split('-')
        camera_id = parts[0] if len(parts) > 0 else "Unknown"
        date_str = parts[1] if len(parts) > 1 else "20200101"
        time_str = parts[2].split('_')[0] if len(parts) > 2 else "000000"
        
        # Get GPS from EXIF if available
        lat, lon = extract_gps_from_image(image_path)
        
        # If no GPS in EXIF, use mock coordinates based on camera ID
        if lat is None or lon is None:
            if camera_id == "B002T":
                lat = -0.4 + random.uniform(-0.1, 0.1)
                lon = -90.3 + random.uniform(-0.1, 0.1)
            elif camera_id == "B004T":
                lat = -0.6 + random.uniform(-0.1, 0.1)
                lon = -90.5 + random.uniform(-0.1, 0.1)
            else:
                lat = -0.5 + random.uniform(-0.2, 0.2)
                lon = -90.4 + random.uniform(-0.2, 0.2)
        
        results.append({
            "tile_id": filename.replace('.jpg', ''),
            "score": random.uniform(0.6, 0.95),  # Mock confidence score
            "lat": lat,
            "lon": lon,
            "thumb_url": f"/local_image/{filename}",
            "image_url": f"/local_image/{filename}",
            "camera_id": camera_id,
            "date": date_str,
            "time": time_str
        })
    
    return results

def extract_gps_from_image(image_path):
    """Extract GPS coordinates from image EXIF data."""
    if not PIL_AVAILABLE:
        return None, None
        
    try:
        with Image.open(image_path) as img:
            exif = img._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    if TAGS.get(tag) == 'GPSInfo':
                        gps_data = {}
                        for gps_tag, gps_value in value.items():
                            gps_data[GPSTAGS.get(gps_tag, gps_tag)] = gps_value
                        
                        if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                            lat = convert_gps_to_decimal(gps_data['GPSLatitude'], gps_data.get('GPSLatitudeRef', 'N'))
                            lon = convert_gps_to_decimal(gps_data['GPSLongitude'], gps_data.get('GPSLongitudeRef', 'W'))
                            return lat, lon
    except Exception as e:
        print(f"Error extracting GPS from {image_path}: {e}")
    
    return None, None

def convert_gps_to_decimal(gps_coords, ref):
    """Convert GPS coordinates from DMS to decimal format."""
    try:
        degrees = float(gps_coords[0])
        minutes = float(gps_coords[1])
        seconds = float(gps_coords[2])
        
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        
        if ref in ['S', 'W']:
            decimal = -decimal
            
        return decimal
    except:
        return None

def confirm_image(filename):
    """Copy image from positive to confirmed folder."""
    try:
        source = os.path.join(POSITIVE_PATH, filename)
        destination = os.path.join(CONFIRMED_PATH, filename)
        
        if os.path.exists(source):
            shutil.copy2(source, destination)
            return True
        return False
    except Exception as e:
        print(f"Error confirming image {filename}: {e}")
        return False

def reject_image(filename):
    """Move image from positive to negative folder."""
    try:
        source = os.path.join(POSITIVE_PATH, filename)
        destination = os.path.join(NEGATIVE_PATH, filename)
        
        if os.path.exists(source):
            shutil.move(source, destination)
            return True
        return False
    except Exception as e:
        print(f"Error rejecting image {filename}: {e}")
        return False

# Mock data (fallback)
def generate_results():
    return [
        {
            "tile_id": f"tile-{i:05d}",
            "score": random.random(),
            "lat": -0.5 + random.random() * 0.5,
            "lon": -90.5 + random.random() * 0.5,
            "thumb_url": f"https://picsum.photos/150/150?random={i}"
        } for i in range(30)
    ]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Tortoise Finder - Detection Platform</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {
            --primary: #059669;
            --primary-dark: #047857;
            --secondary: #0891b2;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-400: #9ca3af;
            --gray-500: #6b7280;
            --gray-600: #4b5563;
            --gray-700: #374151;
            --gray-800: #1f2937;
            --gray-900: #111827;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        }
        
        * { box-sizing: border-box; }
        
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; 
            margin: 0; 
            background: linear-gradient(135deg, var(--gray-50) 0%, #ffffff 100%);
            color: var(--gray-700);
            line-height: 1.6;
        }
        
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 20px;
        }
        
        .header { 
            text-align: center; 
            margin-bottom: 40px;
            padding: 40px 0;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--gray-800);
            margin: 0 0 12px 0;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header .subtitle {
            font-size: 1.1rem;
            color: var(--gray-500);
            font-weight: 400;
        }
        .controls-card { 
            background: white; 
            padding: 32px; 
            border-radius: 16px; 
            margin-bottom: 24px;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--gray-200);
        }
        
        .controls-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--gray-800);
            margin: 0 0 24px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .control-row { 
            display: grid; 
            grid-template-columns: 2fr 1fr auto;
            gap: 24px; 
            align-items: end; 
        }
        
        .form-group { 
            display: flex;
            flex-direction: column;
        }
        
        label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 500;
            color: var(--gray-700);
            font-size: 0.875rem;
        }
        
        input, select { 
            padding: 12px 16px; 
            border: 2px solid var(--gray-200); 
            border-radius: 8px;
            font-size: 0.875rem;
            transition: all 0.2s ease;
            background: white;
        }
        
        input:focus, select:focus { 
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgb(5 150 105 / 0.1);
        }
        
        .threshold-container {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .threshold-container input[type="range"] {
            flex: 1;
            height: 6px;
            background: var(--gray-200);
            border-radius: 3px;
            outline: none;
            padding: 0;
            border: none;
        }
        
        .threshold-container input[type="range"]::-webkit-slider-thumb {
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--primary);
            cursor: pointer;
            box-shadow: var(--shadow);
        }
        
        .threshold-value {
            font-weight: 600;
            color: var(--primary);
            min-width: 40px;
            text-align: center;
            font-size: 0.875rem;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 0.875rem;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            text-decoration: none;
        }
        
        .btn-primary { 
            background: var(--primary); 
            color: white;
        }
        
        .btn-primary:hover:not(:disabled) { 
            background: var(--primary-dark);
            transform: translateY(-1px);
            box-shadow: var(--shadow-lg);
        }
        
        .btn:disabled { 
            background: var(--gray-400); 
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .btn-secondary {
            background: var(--gray-100);
            color: var(--gray-700);
            border: 1px solid var(--gray-300);
        }
        
        .btn-secondary:hover {
            background: var(--gray-200);
        }
        .status-card { 
            padding: 16px 20px; 
            border-radius: 12px; 
            margin: 16px 0;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .status-card.success { 
            background: rgb(16 185 129 / 0.1); 
            color: var(--success);
            border-left: 4px solid var(--success);
        }
        
        .status-card.info { 
            background: rgb(8 145 178 / 0.1); 
            color: var(--secondary);
            border-left: 4px solid var(--secondary);
        }
        
        .status-card.running { 
            background: rgb(245 158 11 / 0.1); 
            color: var(--warning);
            border-left: 4px solid var(--warning);
        }
        
        .run-id-card {
            background: var(--gray-50);
            border: 1px solid var(--gray-200);
            border-radius: 8px;
            padding: 16px;
            margin: 16px 0;
        }
        
        .run-id-card label {
            margin: 0 0 8px 0;
            font-weight: 600;
            color: var(--gray-600);
        }
        
        .run-id-value {
            font-family: 'Monaco', 'Menlo', monospace; 
            font-size: 0.875rem;
            color: var(--gray-800);
            background: white;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid var(--gray-200);
        }
        
        .review-panel { 
            display: none;
            background: white;
            border-radius: 16px;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--gray-200);
            overflow: hidden;
        }
        
        .review-panel.visible { 
            display: block; 
        }
        
        .review-header {
            background: var(--gray-50);
            padding: 24px 32px;
            border-bottom: 1px solid var(--gray-200);
        }
        
        .review-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--gray-800);
            margin: 0 0 16px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .controls-row {
            display: flex;
            gap: 16px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .tally { 
            margin: 0;
            font-weight: 500;
            color: var(--gray-600);
            background: var(--gray-100);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.875rem;
        }
        
        .gallery-container {
            padding: 32px;
            width: 100%;
            overflow: auto;
        }
        
        .gallery { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-top: 24px;
            min-height: 400px;
            width: 100%;
        }
        
        .result-card { 
            background: white;
            border: 1px solid var(--gray-200); 
            border-radius: 12px; 
            overflow: hidden;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-sm);
        }
        
        .result-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
            border-color: var(--primary);
        }
        
        .result-card img { 
            width: 100%; 
            height: 160px; 
            object-fit: cover;
            border-bottom: 1px solid var(--gray-100);
        }
        
        .result-info { 
            padding: 16px;
            font-size: 0.75rem; 
            color: var(--gray-600); 
            line-height: 1.4;
        }
        
        .result-info .tile-id {
            font-weight: 600;
            color: var(--gray-800);
            margin-bottom: 4px;
        }
        
        .result-info .score {
            color: var(--primary);
            font-weight: 500;
        }
        
        .detection-actions {
            padding: 12px;
            display: flex;
            gap: 8px;
            justify-content: center;
            background: var(--gray-50);
            border-top: 1px solid var(--gray-200);
        }
        
        .btn-confirm {
            background: var(--success);
            color: white;
            font-size: 0.8rem;
            padding: 8px 16px;
        }
        
        .btn-confirm:hover {
            background: #059669;
        }
        
        .btn-reject {
            background: var(--error);
            color: white;
            font-size: 0.8rem;
            padding: 8px 16px;
        }
        
        .btn-reject:hover {
            background: #dc2626;
        }
        
        .confirmed-badge {
            position: absolute;
            top: 8px;
            right: 8px;
            background: var(--success);
            color: white;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .rejected-badge {
            position: absolute;
            top: 8px;
            right: 8px;
            background: var(--error);
            color: white;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .export-section { 
            display: flex; 
            gap: 16px; 
            align-items: center;
            background: var(--gray-50);
            padding: 24px 32px;
            border-top: 1px solid var(--gray-200);
        }
        
        .url-output { 
            font-family: 'Monaco', 'Menlo', monospace; 
            font-size: 0.75rem; 
            word-break: break-all;
            background: white;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid var(--gray-200);
            margin-top: 16px;
        }
        
        .loading-spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--gray-500);
        }
        
        .empty-state i {
            font-size: 3rem;
            margin-bottom: 16px;
            color: var(--gray-300);
        }
        
        /* Tab Navigation */
        .tab-navigation {
            display: flex;
            background: white;
            border-radius: 12px;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--gray-200);
            margin-bottom: 24px;
            overflow: hidden;
        }
        
        .tab-button {
            flex: 1;
            padding: 16px 24px;
            background: transparent;
            border: none;
            cursor: pointer;
            font-weight: 500;
            color: var(--gray-600);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
            justify-content: center;
            border-right: 1px solid var(--gray-200);
        }
        
        .tab-button:last-child {
            border-right: none;
        }
        
        .tab-button.active {
            background: var(--primary);
            color: white;
        }
        
        .tab-button:hover:not(.active) {
            background: var(--gray-50);
            color: var(--gray-800);
        }
        
        .tab-panel {
            display: none;
            width: 100%;
        }
        
        .tab-panel.active {
            display: block;
        }
        
        /* Validation gallery must always have size when visible */
        #validation-tab .gallery-container {
            display: block !important;
            width: 100% !important;
            padding: 32px !important;
        }
        
        #validation-tab #validation-gallery {
            display: grid !important;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)) !important;
            gap: 12px !important;
            min-height: 320px !important;
            width: 100% !important;
            min-width: 600px !important;
        }
        
        /* Map must have an explicit height */
        #map { 
            height: 600px; 
            min-height: 400px; 
            width: 100%; 
        }
        
        /* Validation Interface */
        .validation-card {
            display: block;
            background: white;
            border-radius: 16px;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--gray-200);
            overflow: hidden;
            margin-bottom: 24px;
        }
        
        .validation-header {
            background: var(--gray-50);
            padding: 24px 32px;
            border-bottom: 1px solid var(--gray-200);
        }
        
        .validation-controls {
            display: flex;
            gap: 16px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .validation-item {
            background: white;
            border: 2px solid var(--gray-400);
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.2s ease;
            position: relative;
            min-height: 280px;
        }
        
        .validation-item.verified {
            border-color: var(--success);
            box-shadow: 0 0 0 3px rgb(16 185 129 / 0.1);
        }
        
        .validation-item.rejected {
            border-color: var(--error);
            box-shadow: 0 0 0 3px rgb(239 68 68 / 0.1);
        }
        
        .validation-item img {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        
        .validation-actions {
            padding: 16px;
            display: flex;
            gap: 8px;
            justify-content: center;
        }
        
        .btn-verify {
            background: var(--success);
            color: white;
        }
        
        .btn-verify:hover {
            background: #059669;
        }
        
        .btn-reject {
            background: var(--error);
            color: white;
        }
        
        .btn-reject:hover {
            background: #dc2626;
        }
        
        .validation-status {
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .validation-status.verified {
            background: var(--success);
        }
        
        .validation-status.rejected {
            background: var(--error);
        }
        
        /* Map Container */
        .map-container {
            background: white;
            border-radius: 16px;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--gray-200);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            gap: 0;
        }

        .map-stats {
            background: var(--gray-50);
            padding: 24px 32px;
            border-bottom: 1px solid var(--gray-200);
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
        }

        .stat-item {
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 500;
            background: white;
            border-radius: 12px;
            padding: 12px 16px;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--gray-200);
        }

        .stat-item i {
            font-size: 1.4rem;
            color: var(--primary);
        }

        .stat-number {
            background: var(--primary);
            color: white;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.875rem;
        }

        .map-layout {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            padding: 24px 32px 32px;
        }

        .map-main {
            flex: 1 1 520px;
            min-width: 0;
            min-height: 520px;
        }

        #map {
            width: 100%;
            height: 100%;
            min-height: 520px;
        }

        .map-preview {
            flex: 0 1 360px;
            max-width: 420px;
            background: var(--gray-50);
            border: 1px solid var(--gray-200);
            border-radius: 12px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            box-shadow: var(--shadow-sm);
        }

        .map-preview h4 {
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--gray-800);
        }

        .preview-placeholder {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 12px;
            color: var(--gray-500);
            text-align: center;
        }

        .preview-placeholder i {
            font-size: 2rem;
            color: var(--primary);
        }

        .preview-content {
            display: none;
            flex-direction: column;
            gap: 16px;
        }

        .preview-content.visible {
            display: flex;
        }

        #map-preview-image {
            width: 100%;
            border-radius: 12px;
            box-shadow: var(--shadow-md);
            object-fit: contain;
            max-height: 360px;
            background: #000;
        }

        .preview-meta {
            display: grid;
            gap: 8px;
            font-size: 0.9rem;
            color: var(--gray-600);
        }

        .preview-meta strong {
            color: var(--gray-800);
        }

        .preview-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }

        .preview-actions a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
        }
        
        @media (max-width: 768px) {
            .container { padding: 16px; }
            .control-row { 
                grid-template-columns: 1fr; 
                gap: 16px;
            }
            .gallery { 
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 16px;
            }
            .controls-row { 
                flex-direction: column;
                align-items: stretch;
            }
            .header h1 { font-size: 2rem; }
            .map-layout {
                flex-direction: column;
                padding: 16px;
            }
            .map-main {
                min-height: 420px;
            }
            #map {
                min-height: 420px;
            }
            .map-preview {
                width: 100%;
                max-width: none;
            }
        }

    /* Tabs */
.tab-panel {
  display: none;
  width: 100%;
}

.tab-panel.active {
  display: block;
}

/* Validation grid must never collapse */
#validation-gallery {
  display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  min-height: 240px;  /* prevents 0-height */
  width: 100%;
}

/* Map needs explicit height */
#gps-map { height: 600px; min-height: 400px; width: 100%; }
/* Validation grid — never collapses and always targeted within its panel */
#validation-tab #validation-gallery {
  display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)) !important;
  gap: 12px !important;
  min-height: 320px !important;
  width: 100% !important;
}

/* Map must have a real height (support both ids) */
#map, #gps-map { height: 600px !important; min-height: 400px !important; width: 100% !important; }

/* Prevent parent container from zeroing width/height */
#validation-tab, #map-tab { min-height: 360px; }


    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Tortoise Finder</h1>
            <p class="subtitle">Review and confirm images with predicted tortoises</p>
        </div>
        
        <div class="controls-card">
            <h2 class="controls-title">
                <i class="fas fa-cog"></i>
                Model Configuration
            </h2>
            <div class="control-row">
                <div class="form-group">
                    <label for="dataset">
                        <i class="fas fa-database"></i>
                        Dataset URI
                    </label>
                    <input type="text" id="dataset" value="s3://tortoise-artifacts/datasets/demo" placeholder="Enter dataset location...">
                </div>
                <div class="form-group">
                    <label for="threshold">
                        <i class="fas fa-sliders-h"></i>
                        Confidence Threshold
                    </label>
                    <div class="threshold-container">
                    <input type="range" id="threshold" min="0" max="1" step="0.01" value="0.8">
                        <span id="threshold-value" class="threshold-value">0.8</span>
                </div>
                </div>
                <button id="run-btn" class="btn btn-primary" onclick="startRun()">
                    <i class="fas fa-play"></i>
                    Start Model Run
                </button>
            </div>
        </div>
        
        <div id="run-id-section" class="run-id-card" style="display: none;">
            <label>
                <i class="fas fa-fingerprint"></i>
                Run ID
            </label>
            <div id="run-id" class="run-id-value"></div>
        </div>
        
        <div id="status"></div>
        
        <!-- Simple Tab Navigation -->
        <div class="tab-navigation">
            <button id="det-btn" class="tab-button active" onclick="showTab('detection')">
                <i class="fas fa-search"></i>
                Detection
            </button>
            <button id="val-btn" class="tab-button" onclick="showTab('validation')">
                <i class="fas fa-check-double"></i>
                Validation
            </button>
            <button id="map-btn" class="tab-button" onclick="showTab('map')">
                <i class="fas fa-map-marked-alt"></i>
                GPS Map
            </button>
        </div>
        
        <!-- Detection Tab -->
        <section id="detection-tab" class="tab-panel active">
        <div id="review-panel" class="review-panel">
            <div class="review-header">
                <h3 class="review-title">
                    <i class="fas fa-chart-bar"></i>
                    Detection Results
                </h3>
                <div class="controls-row">
                <label>Page:</label>
                <input type="number" id="page" value="1" min="1" style="width: 80px;">
                <label>Page size:</label>
                <select id="page-size">
                    <option value="20">20</option>
                    <option value="40" selected>40</option>
                    <option value="80">80</option>
                </select>
                    <button class="btn btn-secondary" onclick="refreshResults()">
                        <i class="fas fa-sync-alt"></i>
                        Refresh
                    </button>
                    <div class="tally" id="tally">Total: 0 | Page 1/1</div>
                </div>
            </div>
            
            <div class="gallery-container">
                <div id="gallery" class="gallery">
                    <div class="empty-state">
                        <i class="fas fa-search"></i>
                        <p>No detections found yet. Start a run to see results.</p>
                    </div>
                </div>
            </div>
            
            <div class="export-section">
                <label>
                    <i class="fas fa-download"></i>
                    Export format:
                </label>
                <select id="export-format">
                    <option value="geojson">GeoJSON</option>
                    <option value="csv">CSV</option>
                    <option value="gpx">GPX</option>
                    <option value="kml">KML</option>
                </select>
                <button class="btn btn-primary" onclick="exportResults()">
                    <i class="fas fa-file-export"></i>
                    Export Results
                </button>
                
                <div id="download-url-section" style="display: none;">
                    <label>
                        <i class="fas fa-link"></i>
                        <strong>Download URL:</strong>
                    </label>
                <div id="download-url" class="url-output"></div>
            </div>
        </div>
        </section>

        <!-- Validation Tab -->
        <section id="validation-tab" class="tab-panel" hidden>
            <div class="validation-card">
                <div class="validation-header">
                    <h3 class="review-title">
                        <i class="fas fa-check-double"></i>
                        Image Validation
                    </h3>
                    <div class="validation-controls">
                        <label>Filter:</label>
                        <select id="validation-filter">
                            <option value="all">All Images</option>
                            <option value="pending">Pending Review</option>
                            <option value="verified">Verified</option>
                            <option value="rejected">Rejected</option>
                        </select>
                        <button class="btn btn-secondary" onclick="loadValidationImagesScoped()">
                            <i class="fas fa-sync-alt"></i>
                            Refresh
                        </button>
                        <div class="tally" id="validation-tally">Total: 0 | Verified: 0 | Rejected: 0</div>
                    </div>
                </div>
                
                <div class="gallery-container">
                    <div id="validation-gallery" class="gallery">
                        <div style="background: green; color: white; padding: 20px; margin: 10px; font-size: 18px;">
                            VALIDATION TAB CONTENT - This is different from Detection tab
                        </div>
                        <div class="empty-state">
                            <i class="fas fa-images"></i>
                            <p>No confirmed images available for validation yet.</p>
                            <small>Use the Detection tab to confirm some images first.</small>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Map Tab -->
        <section id="map-tab" class="tab-panel" hidden>
            <div class="map-container">
                <div class="map-stats">
                    <div class="stat-item">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>Verified Locations:</span>
                        <span class="stat-number" id="verified-count">0</span>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-calendar"></i>
                        <span>Date Range:</span>
                        <span id="date-range">No data</span>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-camera"></i>
                        <span>Camera Traps:</span>
                        <span class="stat-number" id="camera-count">0</span>
                    </div>
                </div>
                <div class="map-layout">
                    <div class="map-main">
                        <div id="map"></div>
                    </div>
                    <aside class="map-preview" id="map-preview">
                        <h4><i class="fas fa-image"></i> Image Preview</h4>
                        <div class="preview-placeholder" id="map-preview-placeholder">
                            <i class="fas fa-location-arrow"></i>
                            <p>Select a GPS point to preview the confirmed image.</p>
                        </div>
                        <div class="preview-content" id="map-preview-content">
                            <img id="map-preview-image" src="" alt="Selected detection preview">
                            <div class="preview-meta" id="map-preview-meta"></div>
                            <div class="preview-actions">
                                <a id="map-preview-link" href="#" target="_blank" rel="noopener">
                                    <i class="fas fa-external-link-alt"></i>
                                    Open full image
                                </a>
                            </div>
                        </div>
                    </aside>
                </div>
            </div>
        </section>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let currentRunId = 'local';
        let statusTimer = null;
        let validationData = new Map(); // Store validation results
        let map = null;
        let verifiedMarkers = [];
        let currentGpsPoints = [];

        const previewContainer = document.getElementById('map-preview');
        const previewPlaceholder = document.getElementById('map-preview-placeholder');
        const previewContent = document.getElementById('map-preview-content');
        const previewImage = document.getElementById('map-preview-image');
        const previewMeta = document.getElementById('map-preview-meta');
        const previewLink = document.getElementById('map-preview-link');

        function resetPreview() {
            if (!previewContainer) return;
            if (previewPlaceholder) {
                previewPlaceholder.style.display = 'flex';
            }
            if (previewContent) {
                previewContent.classList.remove('visible');
            }
            if (previewImage) {
                previewImage.src = '';
                previewImage.alt = 'Selected detection preview';
                previewImage.style.display = 'none';
            }
            if (previewLink) {
                previewLink.href = '#';
                previewLink.style.visibility = 'hidden';
            }
            if (previewMeta) {
                previewMeta.innerHTML = '';
            }
        }

        function showPreview(point) {
            if (!previewContainer) return;

            if (previewPlaceholder) {
                previewPlaceholder.style.display = 'none';
            }
            if (previewContent) {
                previewContent.classList.add('visible');
            }

            if (previewImage) {
                if (point.image_url) {
                    previewImage.src = point.image_url;
                    previewImage.alt = point.tile_id || 'Confirmed detection';
                    previewImage.style.display = 'block';
                } else {
                    previewImage.src = '';
                    previewImage.alt = 'No preview available';
                    previewImage.style.display = 'none';
                }
            }

            if (previewLink) {
                if (point.image_url) {
                    previewLink.href = point.image_url;
                    previewLink.style.visibility = 'visible';
                } else {
                    previewLink.href = '#';
                    previewLink.style.visibility = 'hidden';
                }
            }

            if (previewMeta) {
                const metaParts = [];
                const info = parseTileMeta(point.tile_id);
                if (info.camera) {
                    metaParts.push(`<span><strong>Camera:</strong> ${info.camera}</span>`);
                }
                if (info.date) {
                    metaParts.push(`<span><strong>Date:</strong> ${info.date}</span>`);
                }
                if (info.time) {
                    metaParts.push(`<span><strong>Time:</strong> ${info.time}</span>`);
                }
                if (Number.isFinite(point.lat) && Number.isFinite(point.lon)) {
                    metaParts.push(`<span><strong>Latitude:</strong> ${point.lat.toFixed(5)}</span>`);
                    metaParts.push(`<span><strong>Longitude:</strong> ${point.lon.toFixed(5)}</span>`);
                }
                previewMeta.innerHTML = metaParts.join('');
            }
        }

        function parseTileMeta(tileId) {
            if (!tileId) return {};
            const parts = tileId.split('-');
            const info = {};
            if (parts.length) {
                info.camera = parts[0];
            }
            if (parts.length > 1 && /^\d{8}$/.test(parts[1])) {
                info.date = `${parts[1].slice(0, 4)}-${parts[1].slice(4, 6)}-${parts[1].slice(6, 8)}`;
            }
            if (parts.length > 2) {
                const timeMatch = parts[2].match(/(\d{6})/);
                if (timeMatch) {
                    const t = timeMatch[1];
                    info.time = `${t.slice(0, 2)}:${t.slice(2, 4)}:${t.slice(4, 6)}`;
                }
            }
            return info;
        }

        function createMarker(point) {
            if (!map || !Number.isFinite(point.lat) || !Number.isFinite(point.lon)) {
                return null;
            }

            const marker = L.marker([point.lat, point.lon], {
                title: point.tile_id || 'Confirmed detection'
            });

            const tooltipLabel = point.tile_id ? point.tile_id.split('.')[0] : 'Confirmed detection';
            marker.bindTooltip(tooltipLabel, { direction: 'top', offset: [0, -10] });

            const popupHtml = `
                <div style="text-align: left; max-width: 220px;">
                    <strong>${point.tile_id || 'Confirmed detection'}</strong><br>
                    <small>Lat: ${point.lat.toFixed(5)}, Lon: ${point.lon.toFixed(5)}</small><br>
                    ${point.image_url ? `<a href="${point.image_url}" target="_blank" rel="noopener">Open image in new tab</a>` : '<em>No image available</em>'}
                </div>`;
            marker.bindPopup(popupHtml);
            marker.on('click', () => showPreview(point));
            marker.addTo(map);
            verifiedMarkers.push(marker);
            return marker;
        }
        
        // Make switchTab available globally with proper layout handling
        /* Single source of truth for tab switching */
    // SIMPLE TAB SYSTEM THAT ACTUALLY WORKS
    function showTab(tabName) {
        console.log('SHOWING TAB:', tabName);

        const tabOrder = ['detection', 'validation', 'map'];
        const buttonIds = { detection: 'det-btn', validation: 'val-btn', map: 'map-btn' };

        tabOrder.forEach(name => {
            const panel = document.getElementById(`${name}-tab`);
            const button = document.getElementById(buttonIds[name]);
            const isActive = name === tabName;

            if (panel) {
                panel.classList.toggle('active', isActive);
                panel.toggleAttribute('hidden', !isActive);
            }

            if (button) {
                button.classList.toggle('active', isActive);
            }
        });

        if (tabName === 'detection') {
            refreshResults();
            document.getElementById('review-panel').classList.add('visible');
        } else if (tabName === 'validation') {
            loadValidationImagesScoped();
            document.getElementById('review-panel').classList.remove('visible');
        } else if (tabName === 'map') {
            if (!map) initializeMap();
            loadGpsData();
            document.getElementById('review-panel').classList.remove('visible');
            if (map) {
                setTimeout(() => map.invalidateSize(), 60);
            }
        }

        console.log('TAB SWITCHED TO:', tabName);
    }
    
    // Make it global
    window.showTab = showTab;

    /* Always scope queries to the active panel so we don't hit hidden clones/templates */
    async function loadValidationImagesScoped() {
    try {
        const r = await fetch('/validation_images?page=1&page_size=40');
        const { items = [] } = await r.json();
        console.log(`Validation: received ${items.length} items`);

        const grid = document.querySelector('#validation-tab #validation-gallery');
        if (!grid) return console.error('Validation: gallery element not found (scoped)');

        if (!items.length) {
        grid.innerHTML = `<div class="empty-state"><i class="fas fa-images"></i><p>No images available for validation.</p></div>`;
        return;
        }

        grid.innerHTML = items.map(item => `
        <div class="validation-item" data-tile-id="${item.tile_id}">
            <img src="${item.thumb_url}" alt="${item.tile_id}">
            <div class="validation-actions">
            <button class="btn btn-verify" onclick="validateImage('${item.tile_id}','verified')"><i class="fas fa-check"></i>Verify</button>
            <button class="btn btn-reject"  onclick="validateImage('${item.tile_id}','rejected')"><i class="fas fa-times"></i>Reject</button>
            </div>
        </div>
        `).join('');

        // Force gallery dimensions to fix 0x0 issue
        grid.style.display = 'grid';
        grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(220px, 1fr))';
        grid.style.gap = '12px';
        grid.style.width = '100%';
        grid.style.minHeight = '320px';
        grid.style.padding = '20px';
        
        // sanity: measure the *visible* gallery only
        const rect = grid.getBoundingClientRect();
        console.log('Validation: visible gallery rect =', rect);
    } catch (err) {
        console.error('Load validation error:', err);
    }
    }
        // Update threshold display
        document.getElementById('threshold').addEventListener('input', function() {
            document.getElementById('threshold-value').textContent = this.value;
                refreshResults();
        });
        
        function startRun() {
            const dataset = document.getElementById('dataset').value;
            const threshold = parseFloat(document.getElementById('threshold').value);
            
            const runBtn = document.getElementById('run-btn');
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="loading-spinner"></span> Starting Detection...';
            
            fetch('/start_run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({dataset, threshold})
            })
            .then(r => r.json())
            .then(data => {
                currentRunId = data.run_id;
                document.getElementById('run-id').textContent = currentRunId;
                document.getElementById('run-id-section').style.display = 'block';
                document.getElementById('review-panel').classList.add('visible');
                
                // Start status polling
                startStatusPolling();
                
                // Initial results fetch
                refreshResults();
            })
            .catch(err => {
                document.getElementById('status').innerHTML = 
                    `<div class="status-card error"><i class="fas fa-exclamation-triangle"></i> Error: ${err.message}</div>`;
                runBtn.disabled = false;
                runBtn.innerHTML = '<i class="fas fa-play"></i> Start Detection';
            });
        }
        
        function startStatusPolling() {
            if (statusTimer) clearInterval(statusTimer);
            
            statusTimer = setInterval(() => {
                if (!currentRunId) return;
                
                fetch(`/status/${currentRunId}`)
                .then(r => r.json())
                .then(data => {
                    const icon = data.state === 'completed' ? 'fas fa-check-circle' : 'fas fa-spinner fa-spin';
                    const statusText = `${data.state} — ${data.progress_pct.toFixed(1)}%`;
                    document.getElementById('status').innerHTML = 
                        `<div class="status-card ${data.state === 'completed' ? 'success' : 'running'}">
                            <i class="${icon}"></i>
                            ${statusText}
                        </div>`;
                    
                    if (data.state === 'completed') {
                        clearInterval(statusTimer);
                        const runBtn = document.getElementById('run-btn');
                        runBtn.disabled = false;
                        runBtn.innerHTML = '<i class="fas fa-play"></i> Start Detection';
                    }
                })
                .catch(err => console.error('Status poll error:', err));
            }, 1500);
        }
        
        function refreshResults() {
            const threshold = parseFloat(document.getElementById('threshold').value);
            const page = parseInt(document.getElementById('page').value);
            const pageSize = parseInt(document.getElementById('page-size').value);
            
            fetch(`/positives?run_id=${currentRunId || 'local'}&threshold=${threshold}&page=${page}&page_size=${pageSize}`)
            .then(r => r.json())
            .then(data => {
                displayGallery(data.items);
                const totalPages = Math.max(1, Math.ceil(data.total / pageSize));
                document.getElementById('tally').textContent = `Total: ${data.total} | Page ${page}/${totalPages}`;
            })
            .catch(err => console.error('Fetch results error:', err));
        }

        // Auto-load from local folders on first paint
        document.addEventListener('DOMContentLoaded', () => {
            // Show review panel by default
            document.getElementById('review-panel').classList.add('visible');
            document.getElementById('run-id-section').style.display = 'none';
            refreshResults();
            
            // Show detection tab by default
            showTab('detection');
        });
        
        function displayGallery(items) {
            const gallery = document.getElementById('gallery');
            
            if (items.length === 0) {
                gallery.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-search"></i>
                        <p>No detections found at this threshold level.</p>
                        <small>Try lowering the confidence threshold to see more results.</small>
                    </div>
                `;
                return;
            }
            
            gallery.innerHTML = items.map(item => {
                const filename = item.tile_id + '.jpg';
                return `
                    <div class="result-card" data-filename="${filename}">
                    <img src="${item.thumb_url}" alt="${item.tile_id}" loading="lazy">
                    <div class="result-info">
                            <div class="tile-id">${item.tile_id}</div>
                            <div class="score">Confidence: ${(item.score * 100).toFixed(1)}%</div>
                            <div><i class="fas fa-map-marker-alt"></i> ${item.lat.toFixed(5)}, ${item.lon.toFixed(5)}</div>
                    </div>
                        <div class="detection-actions">
                            <button class="btn btn-confirm" onclick="confirmImage('${filename}')">
                                <i class="fas fa-check"></i>
                                Confirm
                            </button>
                            <button class="btn btn-reject" onclick="rejectImage('${filename}')">
                                <i class="fas fa-times"></i>
                                Reject
                            </button>
                </div>
                    </div>
                `;
            }).join('');
        }
        
        function exportResults() {
            if (!currentRunId) {
                alert('No run to export!');
                return;
            }
            
            const format = document.getElementById('export-format').value;
            fetch(`/export?run_id=${currentRunId}&fmt=${format}`)
            .then(r => r.json())
            .then(data => {
                document.getElementById('download-url').textContent = data.url;
                document.getElementById('download-url-section').style.display = 'block';
            })
            .catch(err => console.error('Export error:', err));
        }
        
        // Tab Management (duplicate removed - using window.switchTab version)
        
        // Validation Functions
        // Use loadValidationImagesScoped instead - this is a duplicate
        
        // displayValidationGallery removed - functionality merged into loadValidationImagesScoped
        
        function validateImage(tileId, action) {
            validationData.set(tileId, action);
            
            // Update the visual state of the item
            const item = document.querySelector(`[data-tile-id="${tileId}"]`);
            item.className = `validation-item ${action}`;
            
            // Update or add status badge
            let statusBadge = item.querySelector('.validation-status');
            if (!statusBadge) {
                statusBadge = document.createElement('div');
                statusBadge.className = 'validation-status';
                item.appendChild(statusBadge);
            }
            statusBadge.className = `validation-status ${action}`;
            statusBadge.textContent = action.toUpperCase();
            
            updateValidationStats();
            
            // If verified, add to map data
            if (action === 'verified') {
                addToMapData(tileId);
            }
        }
        
        function updateValidationStats() {
            const total = document.querySelectorAll('.validation-item').length;
            const verified = validationData.size ? Array.from(validationData.values()).filter(v => v === 'verified').length : 0;
            const rejected = validationData.size ? Array.from(validationData.values()).filter(v => v === 'rejected').length : 0;
            
            document.getElementById('validation-tally').textContent = 
                `Total: ${total} | Verified: ${verified} | Rejected: ${rejected}`;
        }
        
        // Map Functions
        function initializeMap() {
            // Initialize map centered on Galápagos Islands with base layer control
            const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap contributors'
            });
            const esri = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 19,
                attribution: 'Tiles © Esri'
            });
            map = L.map('map', { layers: [osm] }).setView([-0.5, -90.5], 10);
            L.control.layers({ 'OSM': osm, 'Satellite': esri }).addTo(map);

            resetPreview();
            loadConfirmedLocations();
        }
        
        async function loadGpsData() {
            if (!map) return;

            resetPreview();

            // Clear previous markers
            if (verifiedMarkers.length) {
                verifiedMarkers.forEach(marker => marker.remove());
                verifiedMarkers = [];
            }

            try {
                const r = await fetch('/gps_data');
                const { points = [] } = await r.json();
                const valid = points.filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lon));

                currentGpsPoints = valid;

                if (valid.length) {
                    const markers = valid
                        .map(createMarker)
                        .filter(Boolean);

                    if (markers.length) {
                        const group = L.featureGroup(markers);
                        const bounds = group.getBounds();
                        if (bounds.isValid()) {
                            map.fitBounds(bounds.pad(0.2));
                        }
                    }
                    updateMapStats(valid);
                } else {
                    updateMapStats([]);
                    map.setView([-0.56, -91.55], 11);
                }

                setTimeout(() => map.invalidateSize(), 60);
            } catch (err) {
                console.error('Error loading GPS data:', err);
                updateMapStats([]);
                map.setView([-0.56, -91.55], 10);
                addMockVerifiedLocations();
            }
        }
        
        function loadConfirmedLocations() {
            loadGpsData();
        }
        
        function addMockVerifiedLocations() {
            const mockLocations = [
                { lat: -0.45, lon: -91.55, tile_id: 'Mock-001', image_url: null },
                { lat: -0.41, lon: -91.52, tile_id: 'Mock-002', image_url: null },
            ];

            currentGpsPoints = mockLocations;
            mockLocations.forEach(point => createMarker(point));
            updateMapStats(mockLocations);
        }

        function addToMapData(tileId) {
            // Refresh GPS data so newly confirmed images appear on the map
            if (map) {
                console.log('Refreshing GPS data for', tileId);
                loadGpsData();
            }
        }

        function updateMapStats(points = currentGpsPoints) {
            const verifiedEl = document.getElementById('verified-count');
            const cameraEl = document.getElementById('camera-count');
            const dateRangeEl = document.getElementById('date-range');

            const total = points.length;
            if (verifiedEl) verifiedEl.textContent = total;

            const cameras = new Set();
            const dates = [];
            points.forEach(point => {
                const info = parseTileMeta(point.tile_id);
                if (info.camera) cameras.add(info.camera);
                if (info.date) dates.push(info.date.replace(/-/g, ''));
            });

            if (cameraEl) {
                cameraEl.textContent = cameras.size || 0;
            }

            if (dateRangeEl) {
                if (dates.length) {
                    const sorted = dates.sort();
                    const format = (val) => `${val.slice(0,4)}-${val.slice(4,6)}-${val.slice(6,8)}`;
                    dateRangeEl.textContent = `${format(sorted[0])} - ${format(sorted[sorted.length - 1])}`;
                } else {
                    dateRangeEl.textContent = 'No data';
                }
            }
        }
        
        // Detection Confirm/Reject Functions
        function confirmImage(filename) {
            fetch('/confirm_image', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: filename})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    // Update the card to show confirmed state
                    const card = document.querySelector(`[data-filename="${filename}"]`);
                    if (card) {
                        card.querySelector('.detection-actions').innerHTML = `
                            <div class="confirmed-badge">CONFIRMED</div>
                        `;
                        card.style.borderColor = 'var(--success)';
                        card.style.boxShadow = '0 0 0 3px rgb(16 185 129 / 0.1)';
                    }
                    console.log(`Image ${filename} confirmed and copied to confirmed folder`);
                    
                    // Refresh validation tab if it's active
                    if (document.getElementById('validation-tab').classList.contains('active')) {
                        loadValidationImagesScoped();
                    }
                } else {
                    alert('Failed to confirm image: ' + data.message);
                }
            })
            .catch(err => {
                console.error('Confirm error:', err);
                alert('Error confirming image');
            });
        }
        
        function rejectImage(filename) {
            fetch('/reject_image', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: filename})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    // Update the card to show rejected state
                    const card = document.querySelector(`[data-filename="${filename}"]`);
                    if (card) {
                        card.querySelector('.detection-actions').innerHTML = `
                            <div class="rejected-badge">REJECTED</div>
                        `;
                        card.style.borderColor = 'var(--error)';
                        card.style.boxShadow = '0 0 0 3px rgb(239 68 68 / 0.1)';
                        card.style.opacity = '0.6';
                    }
                    console.log(`Image ${filename} rejected and moved to negative folder`);
                } else {
                    alert('Failed to reject image: ' + data.message);
                }
            })
            .catch(err => {
                console.error('Reject error:', err);
                alert('Error rejecting image');
            });
        }
        
        // Event listeners
        document.getElementById('page').addEventListener('change', refreshResults);
        document.getElementById('page-size').addEventListener('change', refreshResults);
        document.getElementById('validation-filter').addEventListener('change', loadValidationImagesScoped);
    </script>
</body>
</html>
"""

class TortoiseHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
        elif self.path.startswith('/status/'):
            # GET /status/{run_id}
            run_id = self.path.split('/')[-1]
            response = {
                'state': 'completed',
                'progress_pct': 100.0,
                'eta_s': None
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        elif self.path.startswith('/positives'):
            # GET /positives?run_id=...&threshold=...&page=...&page_size=...
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            run_id = params.get('run_id', [''])[0]
            threshold = float(params.get('threshold', ['0.8'])[0])
            page = int(params.get('page', ['1'])[0])
            page_size = int(params.get('page_size', ['40'])[0])
            
            # Use images from positive folder for detection results
            positive_images = get_local_images(POSITIVE_PATH, limit=100)
            if positive_images:
                all_results = positive_images
            else:
                all_results = generate_results()
            
            # Filter by threshold
            filtered = [r for r in all_results if r['score'] >= threshold]
            filtered.sort(key=lambda x: x['score'], reverse=True)
            
            # Paginate
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_results = filtered[start_idx:end_idx]
            
            # Convert to API format
            items = []
            for r in page_results:
                items.append({
                    'tile_id': r['tile_id'],
                    'image_url': r['thumb_url'],
                    'thumb_url': r['thumb_url'],
                    'lat': r['lat'],
                    'lon': r['lon'],
                    'score': r['score']
                })
            
            response = {
                'items': items,
                'total': len(filtered)
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        elif self.path.startswith('/export'):
            # GET /export?run_id=...&fmt=...
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            run_id = params.get('run_id', [''])[0]
            fmt = params.get('fmt', ['geojson'])[0]
            
            # Generate mock export file
            filename = f"tortoise_results_{run_id}.{fmt}"
            
            if fmt == 'geojson':
                geojson = {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [-90.0, -0.5]},
                            "properties": {"tile_id": "demo-001", "score": 0.95}
                        },
                        {
                            "type": "Feature", 
                            "geometry": {"type": "Point", "coordinates": [-90.1, -0.4]},
                            "properties": {"tile_id": "demo-002", "score": 0.87}
                        }
                    ]
                }
                with open(filename, 'w') as f:
                    json.dump(geojson, f, indent=2)
            elif fmt == 'csv':
                with open(filename, 'w') as f:
                    f.write("tile_id,lat,lon,score\n")
                    f.write("demo-001,-0.5,-90.0,0.95\n")
                    f.write("demo-002,-0.4,-90.1,0.87\n")
            elif fmt == 'gpx':
                gpx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="-0.5" lon="-90.0">
    <name>demo-001</name>
    <desc>Score: 0.95</desc>
  </wpt>
  <wpt lat="-0.4" lon="-90.1">
    <name>demo-002</name>
    <desc>Score: 0.87</desc>
  </wpt>
</gpx>'''
                with open(filename, 'w') as f:
                    f.write(gpx_content)
            elif fmt == 'kml':
                kml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>demo-001</name>
      <description>Score: 0.95</description>
      <Point><coordinates>-90.0,-0.5,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>demo-002</name>
      <description>Score: 0.87</description>
      <Point><coordinates>-90.1,-0.4,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>'''
                with open(filename, 'w') as f:
                    f.write(kml_content)
            
            # Return download URL (in real system this would be a presigned S3 URL)
            response = {'url': f'http://localhost:8080/download/{filename}'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        elif self.path.startswith('/local_image/'):
            # Serve local images from positive or confirmed folders
            filename = self.path.split('/')[-1]
            image_path = os.path.join(POSITIVE_PATH, filename)
            
            if not os.path.exists(image_path):
                # Try confirmed folder
                image_path = os.path.join(CONFIRMED_PATH, filename)
            
            if os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Cache-Control', 'max-age=3600')
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()
        elif self.path.startswith('/validation_images'):
            # GET /validation_images?page=1&page_size=20
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            page = int(params.get('page', ['1'])[0])
            page_size = int(params.get('page_size', ['20'])[0])
            
            # Get images from confirmed folder for validation tab
            all_images = get_local_images(CONFIRMED_PATH, limit=200)
            
            # Paginate
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_images = all_images[start_idx:end_idx]
            
            response = {
                'items': page_images,
                'total': len(all_images),
                'page': page,
                'page_size': page_size
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/validation':
            html = """<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
            <title>Tortoise Finder – Validation</title>
            <link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css'>
            <style>
                body{font-family: -apple-system, BlinkMacSystemFont, 'Inter', Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 24px; background:#f6f7fb;}
                .page{max-width:1200px; margin:0 auto;}
                h1{margin:0 0 16px 0; color:#0f766e}
                .gallery{display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:12px; width:100%; min-height:320px}
                .card{background:#fff; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden}
                .card img{width:100%; height:200px; object-fit:cover; display:block}
                .actions{display:flex; gap:8px; padding:10px; justify-content:center}
                .btn{border:none; color:#fff; padding:8px 12px; border-radius:8px; cursor:pointer}
                .verify{background:#10b981}
                .reject{background:#ef4444}
            </style></head><body>
            <div class='page'>
                <h1>Validation_</h1>
                <div id='validation-gallery' class='gallery'></div>
            </div>
            <script>
                async function load(){
                    try{
                        const r = await fetch('/validation_images?page=1&page_size=100');
                        const {items=[]} = await r.json();
                        const g = document.getElementById('validation-gallery');
                        if(!items.length){ g.innerHTML = '<div>No images available.</div>'; return; }
                        g.innerHTML = items.map(it=>`<div class="card"><img src="${it.thumb_url}" alt="${it.tile_id}"><div class="actions"><button class="btn verify" onclick="console.log('verify', '${it.tile_id}')">Verify</button><button class="btn reject" onclick="console.log('reject', '${it.tile_id}')">Reject</button></div></div>`).join('');
                    }catch(e){ console.error('validation load error', e); }
                }
                load();
            </script>
            </body></html>"""
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/map':
            html = """<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
            <title>Tortoise Finder – GPS Map</title>
            <link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>
            <style>
                html,body{height:100%; margin:0}
                #map{height:600px; min-height:400px; width:100%}
                .page{max-width:1200px; margin:0 auto; padding:24px}
                h1{margin:0 0 16px 0; color:#0f766e; font-family: -apple-system, BlinkMacSystemFont, 'Inter', Segoe UI, Roboto, Helvetica, Arial, sans-serif}
            </style></head><body>
            <div class='page'>
                <h1>GPS Map</h1>
                <div id='map'></div>
            </div>
            <script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
            <script>
                let map;
                async function init(){
                    map = L.map('map').setView([-0.6, -90.4], 9);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors' }).addTo(map);
                    try{
                        const r = await fetch('/gps_data');
                        const {points=[]} = await r.json();
                        const valid = points.filter(p => Number.isFinite(p.lat) && Number.isFinite(p.lon));
                        if(valid.length){
                            const markers = valid.map(p => L.marker([p.lat, p.lon]));
                            const fg = L.featureGroup(markers).addTo(map);
                            map.fitBounds(fg.getBounds().pad(0.2));
                        }
                        setTimeout(()=> map.invalidateSize && map.invalidateSize(), 0);
                    }catch(e){ console.error('gps load error', e); }
                }
                init();
            </script>
            </body></html>"""
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/gps_data':
            # GET /gps_data - return GPS coordinates from confirmed images
            points = []
            for fp in glob.glob(os.path.join(CONFIRMED_PATH, "*")):
                fn = os.path.basename(fp)
                if not fn.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue

                lat, lon = extract_gps_from_image(fp)  # may be None
                if lat is None or lon is None:
                    continue

                safe_name = urllib.parse.quote(fn)
                points.append({
                    "lat": lat,
                    "lon": lon,
                    "tile_id": os.path.splitext(fn)[0],
                    "image_url": f"/local_image/{safe_name}"
                })
            
            response = {'points': points}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        elif self.path.startswith('/download/'):
            # Serve exported files
            filename = self.path.split('/')[-1]
            try:
                with open(filename, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                if filename.endswith('.geojson'):
                    self.send_header('Content-type', 'application/geo+json')
                elif filename.endswith('.csv'):
                    self.send_header('Content-type', 'text/csv')
                elif filename.endswith('.gpx'):
                    self.send_header('Content-type', 'application/gpx+xml')
                elif filename.endswith('.kml'):
                    self.send_header('Content-type', 'application/vnd.google-earth.kml+xml')
                else:
                    self.send_header('Content-type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            
            if self.path == '/start_run':
                threshold = data.get('threshold', 0.8)
                run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                
                response = {
                    'job_id': run_id,
                    'run_id': run_id
                }
            
            elif self.path == '/confirm_image':
                filename = data.get('filename')
                success = confirm_image(filename) if filename else False
                
                response = {
                    'success': success,
                    'message': f'Image {filename} confirmed' if success else 'Failed to confirm image'
                }
            
            elif self.path == '/reject_image':
                filename = data.get('filename')
                success = reject_image(filename) if filename else False
                
                response = {
                    'success': success,
                    'message': f'Image {filename} rejected' if success else 'Failed to reject image'
                }
            
            else:
                raise ValueError("Unknown endpoint")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())

if __name__ == "__main__":
    PORT = 8081
    
    with socketserver.TCPServer(("", PORT), TortoiseHandler) as httpd:
        print(f"Tortoise Finder Demo Server")
        print(f"Open your browser to: http://localhost:{PORT}")
        print(f"Press Ctrl+C to stop")
        print("=" * 50)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\nServer stopped!")
            httpd.shutdown()
