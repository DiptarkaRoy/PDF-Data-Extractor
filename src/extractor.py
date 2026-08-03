"""
Module: extractor.py
Description: Structured data extraction engine using a local LLM via Ollama.
"""
import os
from typing import Optional, Dict, Type
from pydantic import BaseModel, Field
import ollama

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

# Configuration Mapping: Category -> (Schema, Prompt Instruction)
CATEGORY_MAPPING: Dict[str, tuple[Type[BaseModel], str]] = {
    "Invoices": (
        InvoiceData, 
        "Extract the Invoice Number, Shipping/Delivery Address, Total Amount, and Currency from this invoice text."
    ),
    "Customs_Declarations": (
        CustomsDeclarationData, 
        "Extract the Customs Declaration/Bill of Entry Number and the Filing Date from this customs document."
    ),
    "Packing_Lists": (
        PackingListData, 
        "Extract the Purchase Order (PO) Number from this packing list."
    )
}

# --- 2. LOCAL EXTRACTION RUNNER ---

def extract_structured_data(
    text: str, 
    category: str, 
    model_name: Optional[str] = None
) -> Optional[str]:
    """
    Passes raw PDF text to a local LLM model using structured Pydantic schema enforcement.
    """
    if category not in CATEGORY_MAPPING:
        print(f"⚠️ Unsupported category: '{category}'")
        return None
    
    active_model = model_name or os.getenv("OLLAMA_MODEL", "llama3.2")
    host_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")    

    schema_cls, prompt = CATEGORY_MAPPING[category]

    try:
        response = ollama.chat(
            model=active_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise data extraction assistant. Extract target values into JSON matching the given schema. Return null or empty strings for missing fields."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nDocument Text:\n{text}"
                }
            ],
            # Pass the Pydantic schema directly to enforce JSON structure
            format=schema_cls.model_json_schema(),
            options={
                "temperature": 0.0  # Zero temperature for deterministic extraction
            }
        )

        return response.message.content

    except Exception as e:
        print(f"❌ Local LLM Extraction error for category '{category}': {e}")
        return None