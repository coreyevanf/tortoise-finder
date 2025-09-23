#!/usr/bin/env python3
"""
Script to upload training images and annotations to S3 storage.
Usage: python scripts/upload_training_data.py <image_dir> <label> [--annotations <annotation_dir>]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from storage.io import put_file, ensure_bucket
from storage.paths import training_image_key, training_annotation_key

def upload_training_images(image_dir: str, label: str, annotation_dir: str = None, split: str = "raw"):
    """Upload training images and annotations to S3."""
    bucket = os.environ["ARTIFACT_BUCKET"]
    ensure_bucket(bucket)
    
    image_path = Path(image_dir)
    if not image_path.exists():
        print(f"Error: Image directory {image_dir} not found")
        return False
    
    # Upload images
    image_files = list(image_path.glob("*.jpg")) + list(image_path.glob("*.png")) + list(image_path.glob("*.jpeg"))
    
    print(f"Uploading {len(image_files)} {label} images...")
    
    for img_file in image_files:
        image_id = img_file.stem
        key = training_image_key(f"{image_id}{img_file.suffix}", split, label)
        
        # Determine content type
        content_type = "image/jpeg" if img_file.suffix.lower() in ['.jpg', '.jpeg'] else "image/png"
        
        print(f"Uploading: {img_file.name} -> {key}")
        put_file(bucket, key, str(img_file), content_type)
        
        # Upload annotation if provided
        if annotation_dir:
            annotation_path = Path(annotation_dir) / f"{image_id}.json"
            if annotation_path.exists():
                annotation_key = training_annotation_key(image_id, split, label)
                print(f"Uploading annotation: {annotation_path.name} -> {annotation_key}")
                put_file(bucket, annotation_key, str(annotation_path), "application/json")
            else:
                print(f"Warning: No annotation found for {image_id}")
    
    print(f"Successfully uploaded {len(image_files)} {label} images!")
    return True

def create_dataset_manifest(image_dir: str, label: str, split: str = "raw"):
    """Create a manifest file listing all uploaded images."""
    bucket = os.environ["ARTIFACT_BUCKET"]
    
    image_path = Path(image_dir)
    image_files = list(image_path.glob("*.jpg")) + list(image_path.glob("*.png")) + list(image_path.glob("*.jpeg"))
    
    manifest = {
        "dataset": f"{label}_{split}",
        "label": label,
        "split": split,
        "count": len(image_files),
        "images": []
    }
    
    for img_file in image_files:
        image_id = img_file.stem
        manifest["images"].append({
            "id": image_id,
            "filename": img_file.name,
            "s3_key": training_image_key(f"{image_id}{img_file.suffix}", split, label),
            "annotation_key": training_annotation_key(image_id, split, label)
        })
    
    # Save manifest
    manifest_path = f"training/{split}/manifests/{label}_manifest.json"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        json.dump(manifest, tmp, indent=2)
        put_file(bucket, manifest_path, tmp.name, "application/json")
        os.unlink(tmp.name)
    
    print(f"Created manifest: {manifest_path}")
    return manifest

if __name__ == "__main__":
    import tempfile
    
    parser = argparse.ArgumentParser(description="Upload training images to S3")
    parser.add_argument("image_dir", help="Directory containing training images")
    parser.add_argument("label", choices=["positive", "negative"], help="Image label (positive/negative)")
    parser.add_argument("--annotations", help="Directory containing annotation files")
    parser.add_argument("--split", default="raw", help="Data split (raw, processed, etc.)")
    parser.add_argument("--manifest", action="store_true", help="Create dataset manifest")
    
    args = parser.parse_args()
    
    success = upload_training_images(args.image_dir, args.label, args.annotations, args.split)
    
    if success and args.manifest:
        create_dataset_manifest(args.image_dir, args.label, args.split)
