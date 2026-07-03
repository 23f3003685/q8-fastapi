import json
import time
import uuid
from collections import deque

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, CONTENT_TYPE_LATEST, generate_latest

app = FastAPI()

# Startup time
START_TIME = time.time()

# Keep last 1000 logs
LOGS = deque(maxlen=1000)

# Prometheus Counter
HTTP_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP Requests",
)

# Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):

    request_id = str(uuid.uuid4())

    response = await call_next(request)

    # Increment counter for EVERY request
    HTTP_COUNTER.inc()

    entry = {
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id,
    }

    LOGS.append(entry)

    print(json.dumps(entry))

    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/work")
async def work(n: int = 1):

    # simulate K units of work
    total = 0
    for i in range(n):
        total += i

    return {
        "email": "your_email@example.com",
        "done": n,
    }


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_s": time.time() - START_TIME,
    }


@app.get("/logs/tail")
async def logs_tail(limit: int = 10):

    if limit < 0:
        limit = 0

    return list(LOGS)[-limit:]


@app.get("/metrics")
async def metrics():

    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )