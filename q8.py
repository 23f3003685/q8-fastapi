from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import re

app = FastAPI()


# ---------------- Models ----------------
class InvoiceRequest(BaseModel):
    text: str


class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str = Field(pattern="^[A-Z]{3}$")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


# ---------------- Vendor ----------------
def extract_vendor(text: str):
    patterns = [
        r"Invoice from\s*[:\-]?\s*(.+?)\s*(?:\||$)",
        r"Vendor\s*[:\-]?\s*(.+?)\s*(?:\||$)",
        r"Billed to\s*[:\-]?\s*(.+?)\s*(?:\||$)"
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # weak fallback (IMPORTANT: not UNKNOWN)
    m = re.search(r"[A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+)*(?:Ltd\.|LLC|Inc\.|Industries)?", text)
    return m.group(0).strip() if m else None


# ---------------- Amount ----------------
def extract_amount(text: str):
    patterns = [
        r"(?:amount due|total|amount)\s*[:=]?\s*([0-9]+(?:\.[0-9]{1,2})?)",
        r"([0-9]+(?:\.[0-9]{1,2})?)\s*(?:USD|EUR|GBP)",
        r"(?:USD|EUR|GBP)\s*([0-9]+(?:\.[0-9]{1,2})?)"
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            for g in m.groups():
                if g and re.match(r"^[0-9]+(\.[0-9]{1,2})?$", g):
                    return float(g)

    return None


# ---------------- Currency ----------------
def extract_currency(text: str):
    m = re.search(r"\b(USD|EUR|GBP)\b", text)
    return m.group(1) if m else None


# ---------------- Date ----------------
def extract_date(text: str):
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return m.group(0) if m else None


# ---------------- Endpoint ----------------
@app.post("/extract", response_model=InvoiceResponse)
def extract(req: InvoiceRequest):
    text = req.text

    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="Empty input")

    vendor = extract_vendor(text)
    amount = extract_amount(text)
    currency = extract_currency(text)
    date = extract_date(text)

    # IMPORTANT: fail only if totally impossible input
    if vendor is None or amount is None or currency is None or date is None:
        raise HTTPException(status_code=422, detail="Could not extract invoice fields")

    return InvoiceResponse(
        vendor=vendor,
        amount=amount,
        currency=currency,
        date=date
    )