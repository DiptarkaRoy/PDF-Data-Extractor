# PDF Data Extractor Suite 🚀

An end-to-end, automated document intelligence and processing pipeline. The **PDF Data Extractor Suite** periodically ingests email attachments from Gmail via OAuth 2.0, monitors local download directories in real-time, classifies documents using configurable regional keyword rules, extracts structured JSON metadata via the Google Gemini API, and safely routes files into organized processed directories.

---

## 🌟 Key Features

* **Automated Gmail Ingestion:** Periodically polls Gmail for unread messages containing attachments, downloads allowed file types (`.pdf`, `.xlsx`, `.csv`, `.docx`, `.zip`), and updates email status labels to avoid duplicate processing.
* **Real-time Filesystem Observer:** Leverages `watchdog` to instantly detect incoming PDFs in `./downloads`, handling incomplete file writes and file lock transfers safely.
* **Configurable Document Classification:** Reads text layout via `pdfplumber` and applies dynamic region/country marker and keyword mapping rules defined in `config.json`.
* **LLM-Powered Data Extraction:** Uses the official `google-genai` SDK with Pydantic schemas and Gemini models (`gemini-2.5-flash` / `gemini-3.1-flash-lite`) at `temperature=0.0` for structured JSON extraction.
* **Resilient Retry & Error Recovery:** Includes exponential backoff for transient Gemini API rate limits (`429`) and server unavailability (`503`), ensuring extraction failures do not block document routing.
* **Multi-Threaded Concurrent Orchestration:** A unified `main.py` entry point runs background ingestion in a daemon thread while maintaining filesystem watching on the main thread with clean keyboard interrupt handling.

---

## 🏗️ Architecture & Workflow

```
                        ┌────────────────────────┐
                        │    Gmail Inbox Sync    │
                        │      (emails.py)       │
                        └───────────┬────────────┘
                                    │ (Polls unread attachments)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          ./downloads/ Directory                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Real-time Watchdog event)
                                    ▼
                        ┌────────────────────────┐
                        │   Classifier Engine    │
                        │    (classifier.py)     │
                        └───────────┬────────────┘
                                    │ (Matches rules in config.json)
               ┌────────────────────┴────────────────────┐
               ▼                                         ▼
   [ Supporting Documents ]                     [ Key Documents ]
   (Moves raw PDF directly)               (Invoices, Packing Lists, Customs)
               │                                         │
               │                                         ▼
               │                            ┌────────────────────────┐
               │                            │    Gemini Extractor    │
               │                            │     (extractor.py)     │
               │                            └───────────┬────────────┘
               │                                         │ (Extracts structured fields)
               │                                         ▼
               │                            [ Output <file>.json ]
               │                                         │
               └────────────────────┬────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ./processed/<Category>/ Directory                    │
│   (e.g., ./processed/Invoices/, ./processed/Customs_Declarations/)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── emails.py           # Gmail OAuth 2.0 ingestion and attachment handler
│   ├── classifier.py       # Watchdog monitor, layout sniffer, and file router
│   └── extractor.py        # Gemini API structured extraction engine (Pydantic)
├── downloads/              # Landing folder for ingested email attachments
├── processed/              # Routed folder organized by document category
│   ├── Invoices/
│   ├── Packing_Lists/
│   ├── Customs_Declarations/
│   └── Supporting_Documents/
├── config.json             # Country markers and classification keyword rules
├── .env                    # Environment variables (Gemini API key)
├── credentials.json        # Google Cloud OAuth 2.0 Client Credentials
├── token.json              # Generated persistent Gmail user auth token
├── main.py                 # Multi-threaded orchestrator and suite entry point
└── README.md               # Suite documentation
```

---

## ⚙️ Configuration (`config.json`)

Document classification rules are fully dynamic. You can specify regional country markers and category-specific keywords:

```json
{
  "countries": {
    "India": {
      "country_markers": ["gstin", "bill of entry", "tax invoice", "iec"],
      "Invoices": ["tax invoice", "invoice no", "gstin"],
      "Packing_Lists": ["packing list", "net weight", "gross weight"],
      "Customs_Declarations": ["bill of entry", "customs clearance", "icegate"]
    },
    "Germany": {
      "country_markers": ["rechnung", "ust-idnr", "zollerklärung"],
      "Invoices": ["rechnung", "rechnungsnummer", "steuer-nr"],
      "Packing_Lists": ["packliste", "gewicht"],
      "Customs_Declarations": ["zollerklärung", "zollamt"]
    },
    "Global_Default": {
      "country_markers": [],
      "Invoices": ["invoice", "bill to", "total amount", "amount due"],
      "Packing_Lists": ["packing list", "purchase order", "po number"],
      "Customs_Declarations": ["customs declaration", "declaration no", "entry number"]
    }
  }
}
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
* Python 3.10+
* Google Cloud Platform Project with **Gmail API** enabled

### 2. Install Dependencies

Clone the repository and install required packages:

```bash
uv sync
```

### 3. Pull Local LLM Model (Required)

Before running extraction, download your preferred local model using Ollama. By default, extractor.py uses llama3.2:

```bash
# Download the default model (Llama 3.2 3B)
ollama pull llama3.2
```

### 4. Environment Setup (.env)

Create a `.env` file in the root directory to configure your local Ollama instance:

```bash
# Ollama Model & Host Configuration
OLLAMA_MODEL="llama3.2"
OLLAMA_HOST="http://localhost:11434"

```
Note: To switch model without changing python code (e.g. to qwen2.5 or mistral), simply change OLLAMA_MODEL in your .env file.

### 5. Environment & Credentials Setup

1. **Gemini API Key:** Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY="your_gemini_api_key_here"
   ```

2. **Gmail OAuth Credentials:**
   * Download your Client Secret JSON file from Google Cloud Console.
   * Rename it to `credentials.json` and place it in the project root directory.

---

## 💻 Usage

Run the main orchestrator script from the root directory:

```bash
python main.py
```

### Running Components Individually

* **Test Gmail Attachment Ingestion:**
  ```bash
  python -m src.emails
  ```

* **Test Folder Monitoring & Routing:**
  ```bash
  python -m src.classifier
  ```

---

## 🛠️ Supported Document Schemas

Structured JSON field models managed by `extractor.py`:

| Category | Extracted Fields | Pydantic Schema |
| :--- | :--- | :--- |
| **Invoices** | `invoice_number`, `shipping_address`, `total_amount`, `currency` | `InvoiceData` |
| **Customs Declarations** | `declaration_number`, `declaration_date` | `CustomsDeclarationData` |
| **Packing Lists** | `po_number` | `PackingListData` |

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more details.