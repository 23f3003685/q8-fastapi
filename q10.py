from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

app = FastAPI()

EMAIL = "23f3003685@ds.study.iitm.ac.in"

WINDOW = 10
BUCKET_SIZE = 13

rate_store = {}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-0zhox4.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):
    # Request ID
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    # Rate limiting
    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()

    if client_id not in rate_store:
        rate_store[client_id] = []

    # Remove expired timestamps
    rate_store[client_id] = [
        t for t in rate_store[client_id]
        if now - t < WINDOW
    ]

    if len(rate_store[client_id]) >= BUCKET_SIZE:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )
        response.headers["X-Request-ID"] = request_id
        return response

    rate_store[client_id].append(now)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }