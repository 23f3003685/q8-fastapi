from fastapi import FastAPI, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Optional, Dict, List
import time
import uuid
import base64
import json

app = FastAPI()

# =========================
# GIVEN VALUES
# =========================
T = 52
R = 18
WINDOW = 10

# =========================
# DATA STORE
# =========================
orders_db = [{"id": i, "item": f"order_{i}"} for i in range(1, T + 1)]

idempotency_store: Dict[str, Dict] = {}
rate_store: Dict[str, List[float]] = {}

# =========================
# CORS (REQUIRED)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# RATE LIMIT (CRITICAL)
# =========================
def check_rate(client_id: str):
    now = time.time()
    store = rate_store.setdefault(client_id, [])

    # keep only last 10 seconds
    store[:] = [t for t in store if now - t < WINDOW]

    if len(store) >= R:
        retry_after = max(1, int(WINDOW - (now - store[0])))

        return Response(
            content=json.dumps({"detail": "Rate limit exceeded"}),
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": str(retry_after)}
        )

    store.append(now)
    return None


# =========================
# CURSOR HELPERS
# =========================
def encode_cursor(i: int) -> str:
    return base64.urlsafe_b64encode(str(i).encode()).decode()

def decode_cursor(c: Optional[str]) -> int:
    if not c:
        return 0
    try:
        return int(base64.urlsafe_b64decode(c.encode()).decode())
    except:
        return 0


# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def root():
    return {"status": "running"}


@app.get("/ping")
def ping(x_client_id: Optional[str] = Header(None, alias="X-Client-Id")):
    client = x_client_id or "anonymous"

    r = check_rate(client)
    if r:
        return r

    return {"status": "ok"}


# =========================
# 1. IDEMPOTENT POST /orders
# =========================
@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id"),
):
    client = x_client_id or "anonymous"

    r = check_rate(client)
    if r:
        return r

    if not idempotency_key:
        return Response(
            content=json.dumps({"error": "Missing Idempotency-Key"}),
            status_code=400,
            media_type="application/json"
        )

    # return same response if repeated
    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": str(uuid.uuid4()),
        "status": "created"
    }

    idempotency_store[idempotency_key] = order
    return order


# =========================
# 2. CURSOR PAGINATION
# =========================
@app.get("/orders")
def get_orders(
    limit: int = 10,
    cursor: Optional[str] = None,
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id"),
):
    client = x_client_id or "anonymous"

    r = check_rate(client)
    if r:
        return r

    start = decode_cursor(cursor)
    end = min(start + limit, len(orders_db))

    items = orders_db[start:end]

    next_cursor = encode_cursor(end) if end < len(orders_db) else None

    return {
        "items": items,
        "next_cursor": next_cursor
    }