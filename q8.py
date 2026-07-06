from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re

app = FastAPI()

# ======================
# REQUEST MODEL
# ======================
class InvoiceRequest(BaseModel):
    text: str

# ======================
# RESPONSE MODEL (IMPORTANT)
# ======================
class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


# ======================
# HELPERS
# ======================
AMOUNT_REGEX = r"(\d+(?:\.\d+)?)"
DATE_REGEX = r"(\d{4}-\d{2}-\d{2})"
CURRENCY_REGEX = r"\b(USD|EUR|GBP)\b"


# ======================
# EXTRACT ENDPOINT
# ======================
@app.post("/extract", response_model=InvoiceResponse)
def extract_invoice(payload: InvoiceRequest):
    text = payload.text or ""

    if not text.strip():
        raise HTTPException(status_code=422, detail="Empty input")

    try:
        # ----------------------
        # VENDOR (first meaningful line / before amount)
        # ----------------------
        vendor_match = re.search(r"([A-Za-z0-9\-\s&.,]+?(Ltd|Inc|LLC|Industries|Corp)[^\n]*)", text)
        vendor = vendor_match.group(0).strip() if vendor_match else "UNKNOWN"

        # ----------------------
        # AMOUNT
        # ----------------------
        amounts = re.findall(AMOUNT_REGEX, text)
        amount = float(amounts[-1]) if amounts else 0.0  # usually total is last number

        # ----------------------
        # CURRENCY
        # ----------------------
        currency_match = re.search(CURRENCY_REGEX, text)
        currency = currency_match.group(1) if currency_match else "USD"

        # ----------------------
        # DATE
        # ----------------------
        date_match = re.search(DATE_REGEX, text)
        date = date_match.group(1) if date_match else "2026-01-01"

        return InvoiceResponse(
            vendor=vendor,
            amount=round(amount, 2),
            currency=currency,
            date=date
        )

    except Exception:
        # NEVER crash with 500
        raise HTTPException(status_code=422, detail="Could not parse invoice")