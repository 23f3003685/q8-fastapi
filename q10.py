from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time

app = FastAPI()

B = 13
WINDOW = 10

rate_store = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

@app.middleware("http")
async def middleware(request: Request, call_next):
    start = time.time()

    # Request ID
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    # Rate limiting
    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()

    requests = rate_store.setdefault(client_id, [])
    requests[:] = [t for t in requests if now - t < WINDOW]

    if len(requests) >= B:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )
    else:
        requests.append(now)
        response = await call_next(request)

    process_time = time.time() - start

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": "23f3003685@ds.study.iitm.ac.in",
        "request_id": request.state.request_id
    }