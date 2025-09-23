#!/usr/bin/env python3
"""
Script to seed a fake dataset for testing purposes.
This creates sample data in MinIO for the tortoise-finder system.
"""

import os
import random
import tempfile
from PIL import Image, ImageDraw
from storage.io import put_file, ensure_bucket
from storage.paths import dataset_prefix

def create_fake_image(width=512, height=512, seed=None):
    """Create a fake image with some random patterns."""
    if seed:
        random.seed(seed)
    
    # Create a base image with random noise
    img = Image.new('RGB', (width, height), color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    draw = ImageDraw.Draw(img)
    
    # Add some random shapes
    for _ in range(random.randint(5, 15)):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw.ellipse([x1, y1, x2, y2], fill=color)
    
    return img

def seed_dataset(dataset_name="demo", num_images=10):
    """Seed a fake dataset with sample images."""
    bucket = os.environ["ARTIFACT_BUCKET"]
    ensure_bucket(bucket)
    
    dataset_path = dataset_prefix(dataset_name)
    
    print(f"Creating fake dataset '{dataset_name}' with {num_images} images...")
    
    for i in range(num_images):
        # Create fake image
        img = create_fake_image(seed=i)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            img.save(tmp.name, "JPEG")
            
            # Upload to MinIO
            key = f"{dataset_path}/image_{i:04d}.jpg"
            put_file(bucket, key, tmp.name, "image/jpeg")
            
            # Clean up temp file
            os.unlink(tmp.name)
            
        print(f"Uploaded {key}")
    
    print(f"Dataset '{dataset_name}' seeded successfully!")
    print(f"Dataset URI: s3://{bucket}/{dataset_path}")

if __name__ == "__main__":
    import sys
    dataset_name = sys.argv[1] if len(sys.argv) > 1 else "demo"
    num_images = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    seed_dataset(dataset_name, num_images)
