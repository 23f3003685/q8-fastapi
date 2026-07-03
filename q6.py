import json
import time
import uuid
from collections import deque

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from prometheus_client import Counter, CONTENT_TYPE_LATEST, generate_latest

app = FastAPI()

# ----------------------------
# Startup time
# ----------------------------
START_TIME = time.time()

# ----------------------------
# In-memory logs (last 1000)
# ----------------------------
LOGS = deque(maxlen=1000)

# ----------------------------
# Prometheus counter
# ----------------------------
HTTP_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP Requests"
)

# ----------------------------
# Middleware (runs for ALL requests)
# ----------------------------
@app.middleware("http")
async def middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())

    response = await call_next(request)

    # increment AFTER request completes
    HTTP_COUNTER.inc()

    log_entry = {
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id,
    }

    LOGS.append(log_entry)

    print(json.dumps(log_entry))

    response.headers["X-Request-ID"] = request_id

    return response


# ----------------------------
# /work endpoint
# ----------------------------
@app.get("/work")
async def work(n: int = 1):
    total = 0
    for i in range(n):
        total += i

    return {
        "email": "23f3003685@ds.study.iitm.ac.in",
        "done": n
    }


# ----------------------------
# /healthz endpoint
# ----------------------------
@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_s": time.time() - START_TIME
    }


# ----------------------------
# /logs/tail endpoint
# ----------------------------
@app.get("/logs/tail")
async def logs_tail(limit: int = 10):
    if limit < 0:
        limit = 0

    return JSONResponse(list(LOGS)[-limit:])


# ----------------------------
# /metrics endpoint (Prometheus)
# ----------------------------
@app.get("/metrics")
async def metrics():
    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST
    )