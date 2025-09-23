import os
import io
import uuid
import pandas as pd
from minio import Minio
from typing import BinaryIO
from .paths import *

def client():
    return Minio(
        endpoint=os.environ["S3_ENDPOINT"].split("://")[-1],
        access_key=os.environ["S3_ACCESS_KEY"],
        secret_key=os.environ["S3_SECRET_KEY"],
        secure=os.getenv("S3_SECURE", "false").lower() == "true"
    )

def ensure_bucket(bucket: str):
    c = client()
    if not c.bucket_exists(bucket): 
        c.make_bucket(bucket)

def put_bytes(bucket: str, key: str, data: bytes, content_type="application/octet-stream"):
    c = client()
    ensure_bucket(bucket)
    c.put_object(bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)

def put_file(bucket: str, key: str, filepath: str, content_type=None):
    c = client()
    ensure_bucket(bucket)
    c.fput_object(bucket, key, filepath, content_type=content_type)

def get_url(bucket: str, key: str, expires=3600):
    c = client()
    return c.presigned_get_object(bucket, key, expires)
