from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import uuid
import time

app = FastAPI()

# =========================
# ASSIGNED VALUES
# =========================
ALLOWED_ORIGIN = "https://app-0zhox4.example.com"
B = 13
WINDOW = 10

# =========================
# STORAGE
# =========================
rate_store = {}

# =========================
# 1. REQUEST CONTEXT MIDDLEWARE
# =========================
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    request.state.request_id = req_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = req_id
    return response


# =========================
# 2. RATE LIMIT MIDDLEWARE
# =========================
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()
    store = rate_store.setdefault(client_id, [])

    # sliding window
    store[:] = [t for t in store if now - t < WINDOW]

    if len(store) >= B:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )

    store.append(now)

    return await call_next(request)


# =========================
# 3. CORS MIDDLEWARE (STRICT)
# =========================
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin")

    if request.method == "OPTIONS":
        response = Response(status_code=200)
    else:
        response = await call_next(request)

    if origin == ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# =========================
# ENDPOINT
# =========================
@app.get("/ping")
def ping(request: Request):
    return {
        "email": "23f3003685@ds.study.iitm.ac.in",
        "request_id": request.state.request_id
    }