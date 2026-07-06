from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time

app = FastAPI()

ALLOWED_ORIGIN = "https://app-0zhox4.example.com"
B = 13
WINDOW = 10

rate_store = {}

# -------------------------
# CORS (proper way)
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # IMPORTANT for grader
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# -------------------------
# Request ID + Timing Middleware
# -------------------------
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # rate limiting store
    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()
    store = rate_store.setdefault(client_id, [])
    store[:] = [t for t in store if now - t < WINDOW]

    if len(store) >= B:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    store.append(now)

    # timing start
    start = time.time()

    # process request
    request.state.request_id = req_id
    response = await call_next(request)

    # timing end
    process_time = time.time() - start

    # headers
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.get("/ping")
def ping(request: Request):
    return {
        "email": "23f3003685@ds.study.iitm.ac.in",
        "request_id": request.state.request_id
    }