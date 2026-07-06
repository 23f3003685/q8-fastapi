from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict, deque
import time
import uuid

app = FastAPI()

EMAIL = "23f3003685@ds.study.iitm.ac.in"

WINDOW = 10
BUCKET_SIZE = 13

rate_store = defaultdict(deque)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-0zhox4.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


@app.middleware("http")
async def middleware(request: Request, call_next):
    start = time.time()

    # REQUEST ID
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    # RATE LIMIT
    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()

    q = rate_store[client_id]

    while q and now - q[0] > WINDOW:
        q.popleft()

    # IF RATE LIMITED
    if len(q) >= BUCKET_SIZE:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

        # ⚠️ MANUALLY ADD CORS HEADERS (IMPORTANT FIX)
        response.headers["Access-Control-Allow-Origin"] = "https://exam.sanand.workers.dev"
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(time.time() - start)
        return response

    q.append(now)

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(time.time() - start)

    return response


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }