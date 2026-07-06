from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, List
import time
import uuid
import base64

app = FastAPI()

# ======================
# CONFIG
# ======================
T = 52
R = 18
WINDOW = 10

orders_db = [{"id": i, "item": f"order_{i}"} for i in range(1, T + 1)]

idempotency_store: Dict[str, Dict] = {}
rate_store: Dict[str, List[float]] = {}

# ======================
# CORS
# ======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://exam.sanand.workers.dev",
        "https://app-0zhox4.example.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "X-Request-ID"],
)

# ======================
# RATE LIMIT (IMPORTANT FIX)
# ======================
def rate_limit(client_id: str):
    now = time.time()
    store = rate_store.setdefault(client_id, [])

    # remove old requests
    store[:] = [t for t in store if now - t < WINDOW]

    # limit exceeded
    if len(store) >= R:
        retry_after = str(int(WINDOW - (now - store[0])))

        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={
                "Retry-After": retry_after,
            },
        )

    store.append(now)
    return None


# ======================
# CURSOR HELPERS
# ======================
def encode_cursor(i: int) -> str:
    return base64.urlsafe_b64encode(str(i).encode()).decode()


def decode_cursor(c: Optional[str]) -> int:
    if not c:
        return 0
    try:
        return int(base64.urlsafe_b64decode(c.encode()).decode())
    except:
        return 0


# ======================
# HEALTH
# ======================
@app.get("/ping")
def ping(x_client_id: Optional[str] = Header(None, alias="X-Client-Id")):
    client = x_client_id or "anonymous"

    rl = rate_limit(client)
    if rl:
        return rl

    return {"status": "ok"}


# ======================
# IDEMPOTENT CREATE ORDER
# ======================
@app.post("/orders", status_code=201)
def create_order(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id"),
):
    client = x_client_id or "anonymous"

    rl = rate_limit(client)
    if rl:
        return rl

    if not idempotency_key:
        return JSONResponse(status_code=400, content={"error": "Missing Idempotency-Key"})

    # return same order if key exists
    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": str(uuid.uuid4()),
        "status": "created",
    }

    idempotency_store[idempotency_key] = order
    return order


# ======================
# CURSOR PAGINATION
# ======================
@app.get("/orders")
def get_orders(
    limit: int = 10,
    cursor: Optional[str] = None,
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id"),
):
    client = x_client_id or "anonymous"

    rl = rate_limit(client)
    if rl:
        return rl

    start = decode_cursor(cursor)
    end = min(start + limit, len(orders_db))

    items = orders_db[start:end]

    return {
        "items": items,
        "next_cursor": encode_cursor(end) if end < len(orders_db) else None,
    }