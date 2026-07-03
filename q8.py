from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import re
import requests
import json

app = FastAPI()


# ---------------- Request ----------------
class InvoiceRequest(BaseModel):
    text: str


# ---------------- Response ----------------
class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str = Field(pattern="^[A-Z]{3}$")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


# ---------------- LOCAL LLM (Ollama) ----------------
def llm_extract(text: str):
    """
    Uses local Ollama model (llama3/mistral).
    Make sure Ollama is running:
    ollama run llama3
    """

    prompt = f"""
Extract invoice data as STRICT JSON.

Return ONLY JSON:
{{
  "vendor": string,
  "amount": number,
  "currency": "USD" or "EUR" or "GBP",
  "date": "YYYY-MM-DD"
}}

Invoice:
{text}
"""

    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=5
        )

        output = r.json()["response"]

        # try parse JSON from LLM
        return json.loads(output)

    except:
        return None


# ---------------- Regex fallback ----------------
def regex_extract(text: str):
    vendor = re.search(
        r"(?:Invoice from|Vendor|Billed to)\s*[:\-]?\s*(.+?)(?:\||Amount|Total|Due|Deadline|$)",
        text,
        re.I
    )

    amount = re.search(
        r"(?:amount due|total|amount)\s*[:=]?\s*([0-9]+(?:\.[0-9]{1,2})?)",
        text,
        re.I
    ) or re.search(r"([0-9]+(?:\.[0-9]{1,2})?)\s*(USD|EUR|GBP)", text, re.I)

    currency = re.search(r"\b(USD|EUR|GBP)\b", text)
    date = re.search(r"\d{4}-\d{2}-\d{2}", text)

    return {
        "vendor": vendor.group(1).strip() if vendor else None,
        "amount": float(amount.group(1)) if amount else None,
        "currency": currency.group(1) if currency else None,
        "date": date.group(0) if date else None
    }


# ---------------- MAIN ENDPOINT ----------------
@app.post("/extract", response_model=InvoiceResponse)
def extract(req: InvoiceRequest):

    text = req.text

    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="Empty input")

    # 1. Try LLM first
    data = llm_extract(text)

    # 2. Fallback to regex
    if not data:
        data = regex_extract(text)

    # 3. LAST SAFETY CHECK (no fake values!)
    if not data:
        raise HTTPException(status_code=422, detail="Could not extract invoice fields")

    # 4. Validate required fields
    if not all(k in data for k in ["vendor", "amount", "currency", "date"]):
        raise HTTPException(status_code=422, detail="Incomplete extraction")

    # 5. Final cleanup (VERY IMPORTANT)
    return InvoiceResponse(
        vendor=str(data["vendor"]),
        amount=float(data["amount"]),
        currency=str(data["currency"]).upper(),
        date=str(data["date"])
    )