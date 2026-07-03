from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- CONFIG ----------------
API_KEY = "ak_k4vnorqbpda2y1qkg55q0z4i"
EMAIL = "23f3003685@ds.study.iitm.ac.in"


# ---------------- MODELS ----------------
class Event(BaseModel):
    user: str
    amount: float
    ts: int


class Payload(BaseModel):
    events: List[Event]


# ---------------- HEALTH ----------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ---------------- ANALYTICS ----------------
@app.post("/analytics")
def analytics(
    payload: Payload,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    # AUTH CHECK
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    events = payload.events

    total_events = len(events)

    unique_users = set()
    revenue = 0.0
    user_totals = {}

    # PROCESS EVENTS
    for e in events:
        unique_users.add(e.user)

        if e.amount > 0:
            revenue += e.amount
            user_totals[e.user] = user_totals.get(e.user, 0.0) + e.amount

    # TOP USER
    top_user = None
    if user_totals:
        top_user = max(user_totals, key=user_totals.get)

    return {
        "email": EMAIL,
        "total_events": total_events,
        "unique_users": len(unique_users),
        "revenue": revenue,
        "top_user": top_user
    }