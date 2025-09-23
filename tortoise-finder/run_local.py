#!/usr/bin/env python3
"""
Simple local development server for tortoise-finder.
Run this to start the UI without Docker.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'fastapi', 'uvicorn', 'gradio', 'redis', 'rq', 
        'minio', 'pandas', 'pillow', 'requests'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("Installing missing packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing)
    
    return len(missing) == 0

def start_redis():
    """Start Redis server if not running."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✓ Redis is running")
        return True
    except:
        print("⚠ Redis not running. Please start Redis:")
        print("  brew install redis")
        print("  brew services start redis")
        return False

def start_minio():
    """Start MinIO server if not running."""
    try:
        import requests
        response = requests.get('http://localhost:9000/minio/health/live', timeout=2)
        if response.status_code == 200:
            print("✓ MinIO is running")
            return True
    except:
        pass
    
    print("⚠ MinIO not running. Please start MinIO:")
    print("  brew install minio/stable/minio")
    print("  minio server /tmp/minio --console-address :9001")
    return False

def start_api():
    """Start the FastAPI server."""
    print("Starting API server...")
    os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
    os.environ['S3_ENDPOINT'] = 'http://localhost:9000'
    os.environ['S3_ACCESS_KEY'] = 'minioadmin'
    os.environ['S3_SECRET_KEY'] = 'minioadmin'
    os.environ['ARTIFACT_BUCKET'] = 'tortoise-artifacts'
    
    # Start API in background
    api_process = subprocess.Popen([
        sys.executable, '-m', 'uvicorn', 'api.main:app', 
        '--host', '0.0.0.0', '--port', '8000'
    ])
    
    # Wait for API to start
    time.sleep(3)
    return api_process

def start_ui():
    """Start the Gradio UI."""
    print("Starting UI server...")
    os.environ['API_URL'] = 'http://localhost:8000'
    
    # Start UI
    subprocess.run([
        sys.executable, '-m', 'gradio', 'app_ui/ui.py',
        '--server-name', '0.0.0.0', '--server-port', '7860'
    ])

def main():
    print("Starting Tortoise Finder (Local Development)")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Failed to install dependencies")
        return
    
    # Check services
    redis_ok = start_redis()
    minio_ok = start_minio()
    
    if not redis_ok or not minio_ok:
        print("\n⚠️  Some services are not running.")
        print("You can still start the UI, but some features may not work.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Start API
    api_process = start_api()
    
    try:
        # Start UI
        start_ui()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        if api_process:
            api_process.terminate()
            api_process.wait()

if __name__ == "__main__":
    main()
