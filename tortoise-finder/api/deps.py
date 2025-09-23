# Dependencies for the API
from fastapi import Depends
from redis import Redis
from rq import Queue
import os

def get_redis() -> Redis:
    return Redis.from_url(os.environ["REDIS_URL"])

def get_queue(redis: Redis = Depends(get_redis)) -> Queue:
    return Queue(os.environ.get("RQ_QUEUE", "tortoise"), connection=redis)
