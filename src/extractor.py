"""
Module: extractor.py
Description: Structured data extraction engine using Google Gemini API.
"""
import os
import time
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional

# --- 1. DEFINE SCHEMAS FOR EACH DOCUMENT TYPE ---

class InvoiceData(BaseModel):
    invoice_number: Optional[str] = Field(None, description="The unique invoice identifier/number.")
    shipping_address: Optional[str] = Field(None, description="The complete delivery/shipping address.")
    total_amount: Optional[float] = Field(None, description="The final total invoice amount as a float.")
    currency: Optional[str] = Field(None, description="3-letter currency code (e.g., USD, INR, EUR).")

class CustomsDeclarationData(BaseModel):
    declaration_number: Optional[str] = Field(None, description="The customs registration/declaration/bill of entry number.")
    declaration_date: Optional[str] = Field(None, description="The filing or entry date (YYYY-MM-DD format preferred).")

class PackingListData(BaseModel):
    po_number: Optional[str] = Field(None, description="The Purchase Order (PO) number reference.")

# --- 2. EXTRACTION RUNNER ---

def extract_structured_data(text: str, category: str, max_retries: int = 3, initial_delay: int = 2):
    """
    Passes raw PDF text to Gemini with automatic retries on temporary 503/429 server errors.
    """
    if "GEMINI_API_KEY" not in os.environ:
        raise ValueError("Environment variable 'GEMINI_API_KEY' is missing.")

    if category == "Invoices":
        schema = InvoiceData
        prompt = "Extract the Invoice Number, Shipping/Delivery Address, Total Amount, and Currency from this invoice text."
    elif category == "Customs_Declarations":
        schema = CustomsDeclarationData
        prompt = "Extract the Customs Declaration/Bill of Entry Number and the Filing Date from this customs document."
    elif category == "Packing_Lists":
        schema = PackingListData
        prompt = "Extract the Purchase Order (PO) Number from this packing list."
    else:
        return None

    client = genai.Client()
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=f"{prompt}\n\nDocument Text:\n{text}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.0
                ),
            )
            return response.text

        except Exception as e:
            # Check if it's a temporary 503 (Unavailable) or 429 (Rate Limit)
            error_msg = str(e)
            is_transient = "503" in error_msg or "UNAVAILABLE" in error_msg or "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg
            
            if is_transient and attempt < max_retries - 1:
                print(f"⚠️ Gemini busy (Attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2  # Double the wait time for the next try
            else:
                # If it's a structural error (400) or we ran out of retries, raise it to fail gracefully
                print(f"❌ Extraction error for {category} on final attempt: {e}")
                return None