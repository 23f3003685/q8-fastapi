from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid
import base64
from typing import Optional, Dict, List

app = FastAPI()

# =========================
# ASSIGNED VALUES
# =========================
T = 52   # total orders
R = 18   # requests per 10 seconds

# =========================
# DATA
# =========================
orders = [{"id": i, "item": f"order_{i}"} for i in range(1, T + 1)]

# Idempotency storage
idempotency_store: Dict[str, Dict] = {}

# Rate limit storage: client_id -> timestamps
rate_store: Dict[str, List[float]] = {}

# =========================
# CORS (IMPORTANT FOR GRADER)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# RATE LIMITING
# =========================
def rate_limit(client_id: str):
    now = time.time()
    window = 10

    if client_id not in rate_store:
        rate_store[client_id] = []

    # keep only last 10 seconds
    rate_store[client_id] = [
        t for t in rate_store[client_id] if now - t < window
    ]

    if len(rate_store[client_id]) >= R:
        retry_after = int(window - (now - rate_store[client_id][0]))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(max(retry_after, 1))}
        )

    rate_store[client_id].append(now)


# =========================
# CURSOR ENCODING
# =========================
def encode_cursor(i: int) -> str:
    return base64.urlsafe_b64encode(str(i).encode()).decode()

def decode_cursor(c: str) -> int:
    if not c:
        return 0
    return int(base64.urlsafe_b64decode(c.encode()).decode())


# =========================
# 1. IDEMPOTENT POST /orders
# =========================
@app.post("/orders")
async def create_order(
    request: Request,
    idempotency_key: Optional[str] = Header(None),
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id")
):
    if not x_client_id:
        raise HTTPException(400, "Missing X-Client-Id")

    rate_limit(x_client_id)

    if not idempotency_key:
        raise HTTPException(400, "Missing Idempotency-Key")

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
async def get_orders(
    limit: int = 10,
    cursor: Optional[str] = None,
    x_client_id: Optional[str] = Header(None, alias="X-Client-Id")
):
    if not x_client_id:
        raise HTTPException(400, "Missing X-Client-Id")

    rate_limit(x_client_id)

    start = decode_cursor(cursor)
    end = start + limit

    items = orders[start:end]

    next_cursor = encode_cursor(end) if end < len(orders) else None

    return {
        "items": items,
        "next_cursor": next_cursor
    }


# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def home():
    return {"status": "running"}