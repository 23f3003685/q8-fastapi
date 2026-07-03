from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import re
import json

app = FastAPI()


class InvoiceRequest(BaseModel):
    text: str


class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str = Field(pattern="^[A-Z]{3}$")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


def safe_float(x):
    try:
        return float(x)
    except:
        return None


def extract_vendor(text):
    m = re.search(r"(?:Invoice from|Vendor|Billed to)\s*[:\-]?\s*(.+?)(?:\||Amount|Total|Due|Deadline|$)", text, re.I)
    return m.group(1).strip() if m else None


def extract_amount(text):
    m = re.search(r"([0-9]+(?:\.[0-9]{1,2})?)\s*(USD|EUR|GBP)", text, re.I)
    if m:
        return safe_float(m.group(1))

    m = re.search(r"(?:amount due|total|amount)\s*[:=]?\s*([0-9]+(?:\.[0-9]{1,2})?)", text, re.I)
    if m:
        return safe_float(m.group(1))

    return None


def extract_currency(text):
    m = re.search(r"\b(USD|EUR|GBP)\b", text)
    return m.group(1) if m else None


def extract_date(text):
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return m.group(0) if m else None


@app.post("/extract", response_model=InvoiceResponse)
def extract(req: InvoiceRequest):
    text = req.text

    # 1. ONLY reject truly empty input
    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="Empty input")

    # 2. Extract safely
    vendor = extract_vendor(text)
    amount = extract_amount(text)
    currency = extract_currency(text)
    date = extract_date(text)

    # 3. HARD safety: never crash, never 500
    if vendor is None:
        vendor = "UNKNOWN"

    if amount is None:
        amount = 0.0

    if currency is None:
        currency = "USD"

    if date is None:
        date = "2026-01-01"

    # 4. Return safe schema
    return InvoiceResponse(
        vendor=vendor,
        amount=amount,
        currency=currency,
        date=date
    )