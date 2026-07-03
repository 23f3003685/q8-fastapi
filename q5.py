from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# ===== CORS (required by grader browser) =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== API KEY =====
API_KEY = "ak_k4vnorqbpda2y1qkg55q0z4i"

# ===== EMAIL (replace if platform gives yours) =====
EMAIL = "23f3003685@ds.study.iitm.ac.in"


# ===== Request Models =====
class Event(BaseModel):
    user: str
    amount: float
    ts: int


class Payload(BaseModel):
    events: List[Event]


# ===== Endpoint =====
@app.post("/analytics")
def analytics(payload: Payload, request: Request):
    # ---- AUTH ----
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    events = payload.events

    total_events = len(events)

    unique_users = set()
    revenue = 0.0

    user_totals = {}

    # ---- PROCESS EVENTS ----
    for e in events:
        unique_users.add(e.user)

        if e.amount > 0:
            revenue += e.amount
            user_totals[e.user] = user_totals.get(e.user, 0) + e.amount

    # ---- TOP USER ----
    top_user = None
    top_value = float("-inf")

    for user, total in user_totals.items():
        if total > top_value:
            top_value = total
            top_user = user

    return {
        "email": EMAIL,
        "total_events": total_events,
        "unique_users": len(unique_users),
        "revenue": revenue,
        "top_user": top_user
    }


# ===== Health check (optional but good practice) =====
@app.get("/healthz")
def healthz():
    return {"status": "ok"}
