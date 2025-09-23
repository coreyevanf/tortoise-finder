import os
import time
from redis import Redis
from rq import Connection, Worker

if __name__ == "__main__":
    redis = Redis.from_url(os.environ["REDIS_URL"])
    with Connection(redis):
        Worker([os.environ.get("RQ_QUEUE", "tortoise")]).work()
