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
# RESPONSE MODEL
# ======================
class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


# ======================
# CONSTANTS
# ======================
CURRENCY_REGEX = r"\b(USD|EUR|GBP)\b"
DATE_REGEX = r"\b(\d{4}-\d{2}-\d{2})\b"


# ======================
# EXTRACT ENDPOINT
# ======================
@app.post("/extract", response_model=InvoiceResponse)
def extract_invoice(payload: InvoiceRequest):
    text = (payload.text or "").strip()

    if not text:
        raise HTTPException(status_code=422, detail="Empty input")

    try:
        clean_text = text.replace("\n", " ")

        # ======================
        # VENDOR (best-effort)
        # ======================
        vendor_match = re.search(
            r"([A-Za-z0-9\-\s&.,]+?(Ltd|Inc|LLC|Industries|Corp)[^\n]*)",
            clean_text,
            re.IGNORECASE
        )
        vendor = vendor_match.group(0).strip() if vendor_match else "UNKNOWN"

        # ======================
        # AMOUNT (FIXED - CRITICAL)
        # ONLY FROM TOTAL CONTEXT
        # ======================
        amount = 0.0

        total_match = re.search(
            r"(total|amount\s*due|grand\s*total|balance\s*due)[^\d]{0,20}(\d+(?:\.\d+)?)",
            clean_text,
            re.IGNORECASE
        )

        if total_match:
            amount = float(total_match.group(2))
        else:
            # fallback: last number (NOT max, NOT random)
            numbers = re.findall(r"\d+\.\d+|\d+", clean_text)
            amount = float(numbers[-1]) if numbers else 0.0

        # ======================
        # CURRENCY
        # ======================
        currency_match = re.search(CURRENCY_REGEX, clean_text)
        currency = currency_match.group(1).upper() if currency_match else "USD"

        # ======================
        # DATE
        # ======================
        date_match = re.search(DATE_REGEX, clean_text)
        date = date_match.group(1) if date_match else "2026-01-01"

        return InvoiceResponse(
            vendor=vendor,
            amount=round(amount, 2),
            currency=currency,
            date=date
        )

    except Exception:
        raise HTTPException(status_code=422, detail="Could not parse invoice")
