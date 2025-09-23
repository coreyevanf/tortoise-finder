#!/usr/bin/env python3
"""
Script to upload model files to S3 storage.
Usage: python scripts/upload_model.py <model_path> <version> [config_path] [metadata_path]
"""

import os
import sys
import json
from pathlib import Path
from storage.io import put_file, ensure_bucket
from storage.paths import model_weights_key, model_config_key, model_metadata_key

def upload_model(model_path: str, version: str, config_path: str = None, metadata_path: str = None):
    """Upload model files to S3."""
    bucket = os.environ["ARTIFACT_BUCKET"]
    ensure_bucket(bucket)
    
    # Upload model weights
    weights_key = model_weights_key(version)
    print(f"Uploading model weights: {model_path} -> {weights_key}")
    put_file(bucket, weights_key, model_path, "application/octet-stream")
    
    # Upload config if provided
    if config_path and os.path.exists(config_path):
        config_key = model_config_key(version)
        print(f"Uploading config: {config_path} -> {config_key}")
        put_file(bucket, config_key, config_path, "application/json")
    else:
        # Create default config
        default_config = {
            "model_type": "tortoise_detector",
            "version": version,
            "input_size": [512, 512],
            "num_classes": 1,
            "confidence_threshold": 0.5
        }
        config_key = model_config_key(version)
        print(f"Creating default config: {config_key}")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(default_config, tmp, indent=2)
            put_file(bucket, config_key, tmp.name, "application/json")
            os.unlink(tmp.name)
    
    # Upload metadata if provided
    if metadata_path and os.path.exists(metadata_path):
        metadata_key = model_metadata_key(version)
        print(f"Uploading metadata: {metadata_path} -> {metadata_key}")
        put_file(bucket, metadata_key, metadata_path, "application/json")
    else:
        # Create default metadata
        default_metadata = {
            "version": version,
            "upload_date": datetime.utcnow().isoformat(),
            "description": "Tortoise detection model",
            "performance": {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0
            }
        }
        metadata_key = model_metadata_key(version)
        print(f"Creating default metadata: {metadata_key}")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(default_metadata, tmp, indent=2)
            put_file(bucket, metadata_key, tmp.name, "application/json")
            os.unlink(tmp.name)
    
    print(f"Model {version} uploaded successfully!")
    print(f"Model URI: s3://{bucket}/{weights_key}")

if __name__ == "__main__":
    import tempfile
    from datetime import datetime
    
    if len(sys.argv) < 3:
        print("Usage: python scripts/upload_model.py <model_path> <version> [config_path] [metadata_path]")
        sys.exit(1)
    
    model_path = sys.argv[1]
    version = sys.argv[2]
    config_path = sys.argv[3] if len(sys.argv) > 3 else None
    metadata_path = sys.argv[4] if len(sys.argv) > 4 else None
    
    if not os.path.exists(model_path):
        print(f"Error: Model file {model_path} not found")
        sys.exit(1)
    
    upload_model(model_path, version, config_path, metadata_path)
