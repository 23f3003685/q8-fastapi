from fastapi import FastAPI, Header, HTTPException, status
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

# ======================
# DATA
# ======================
orders_db = [{"id": i, "item": f"order_{i}"} for i in range(1, T + 1)]

idempotency_store: Dict[str, Dict] = {}
rate_store: Dict[str, List[float]] = {}

# ======================
# CORS
# ======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# RATE LIMIT (IMPORTANT)
# ======================
def rate_limit(client_id: str):
    now = time.time()
    store = rate_store.setdefault(client_id, [])

    # sliding window (10 sec)
    store[:] = [t for t in store if now - t < WINDOW]

    if len(store) >= R:
        retry_after = max(1, int(WINDOW - (now - store[0])))

        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )

    store.append(now)


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
@app.get("/")
def root():
    return {"status": "running"}


@app.get("/ping")
def ping(x_client_id: Optional[str] = Header(None, alias="X-Client-Id")):
    client = x_client_id or "anonymous"
    rate_limit(client)
    return {"status": "ok"}


# ======================
# POST /orders (IDEMPOTENT)
# ======================
@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id"),
):
    client = x_client_id or "anonymous"
    rate_limit(client)

    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Missing Idempotency-Key")

    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": str(uuid.uuid4()),
        "status": "created"
    }

    idempotency_store[idempotency_key] = order
    return order


# ======================
# GET /orders (CURSOR PAGINATION)
# ======================
@app.get("/orders")
def get_orders(
    limit: int = 10,
    cursor: Optional[str] = None,
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id"),
):
    client = x_client_id or "anonymous"
    rate_limit(client)

    start = decode_cursor(cursor)
    end = min(start + limit, len(orders_db))

    items = orders_db[start:end]

    next_cursor = encode_cursor(end) if end < len(orders_db) else None

    return {
        "items": items,
        "next_cursor": next_cursor
    }