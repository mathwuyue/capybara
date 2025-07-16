import os
from contextlib import asynccontextmanager

import redis
import serve
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from prisma import Prisma
from serve import *

load_dotenv()


# --- FastAPI Application ---
db = Prisma(auto_register=True)


# --- Database Connection Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connection during app lifespan."""
    await db.connect()
    app.state.redis = redis.ConnectionPool.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    try:
        yield
    finally:
        if db.is_connected():
            await db.disconnect()


app = FastAPI(title="HRAI Demo", lifespan=lifespan)


# load all modules in serve/webapi.py
for mod in dir(serve):
    c = getattr(serve, mod, None)
    init_app = getattr(c, "init_app", None)
    if init_app:
        init_app(app)


if __name__ == "__main__":
    # uvicorn.run("server:app", host="0.0.0.0", port=9066, log_config=LOGGING_CONFIG, reload=True)
    uvicorn.run("server:app", host="0.0.0.0", port=19006, reload=True)
