from fastapi import FastAPI, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Dict, List
import time
import uuid
import base64

app = FastAPI()

# ==========================
# ASSIGNED VALUES
# ==========================
T = 52   # Total orders
R = 18   # Requests per 10 seconds

# ==========================
# CORS
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# DATA
# ==========================
orders = [{"id": i, "item": f"order_{i}"} for i in range(1, T + 1)]

idempotency_store: Dict[str, Dict] = {}
rate_store: Dict[str, List[float]] = {}

WINDOW = 10


# ==========================
# CURSOR HELPERS
# ==========================
def encode_cursor(index: int) -> str:
    return base64.urlsafe_b64encode(str(index).encode()).decode()


def decode_cursor(cursor: Optional[str]) -> int:
    if not cursor:
        return 0
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:
        return 0


# ==========================
# RATE LIMIT
# ==========================
def check_rate_limit(client_id: str):
    now = time.time()

    timestamps = rate_store.setdefault(client_id, [])

    # Remove timestamps older than 10 seconds
    timestamps[:] = [t for t in timestamps if now - t < WINDOW]

    if len(timestamps) >= R:
        retry_after = max(
            1,
            int(WINDOW - (now - timestamps[0]))
        )

        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={
                "Retry-After": str(retry_after)
            },
        )

    timestamps.append(now)
    return None


# ==========================
# ROOT
# ==========================
@app.get("/")
def root():
    return {"status": "running"}

@app.get("/ping")
def ping(
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id")
):
    client = x_client_id or "anonymous"

    limited = check_rate_limit(client)
    if limited:
        return limited

    return {"status": "ok"}


# ==========================
# IDEMPOTENT ORDER CREATION
# ==========================
@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id"),
):
    if not idempotency_key:
        return JSONResponse(
            status_code=400,
            content={"detail": "Missing Idempotency-Key"},
        )

    client = x_client_id or "anonymous"

    limited = check_rate_limit(client)
    if limited:
        return limited

    if idempotency_key in idempotency_store:
        # Same response, same order id
        return idempotency_store[idempotency_key]

    order = {
        "id": str(uuid.uuid4()),
        "status": "created"
    }

    idempotency_store[idempotency_key] = order

    return JSONResponse(
        status_code=201,
        content=order,
    )


# ==========================
# CURSOR PAGINATION
# ==========================
@app.get("/orders")
def list_orders(
    limit: int = 10,
    cursor: Optional[str] = None,
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id"),
):
    client = x_client_id or "anonymous"

    limited = check_rate_limit(client)
    if limited:
        return limited

    if limit < 1:
        limit = 1

    start = decode_cursor(cursor)
    end = min(start + limit, len(orders))

    items = orders[start:end]

    next_cursor = None
    if end < len(orders):
        next_cursor = encode_cursor(end)

    return {
        "items": items,
        "next_cursor": next_cursor,
    }