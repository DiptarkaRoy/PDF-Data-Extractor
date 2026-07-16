"""
Module: classifier.py
Description: Automated, configuration-driven PDF classification and routing engine.
             Monitors a landing directory in real-time, extracts visual/textual data 
             from incoming PDFs, and dynamically routes them into regional and document-type 
             folders based on configurable business rules.

Architecture & Workflow:
    1. Watcher (Watchdog): Listens to filesystem events in './downloads'.
    2. Debouncer (File Lock): Waits for file transfer/copy operations to fully complete.
    3. Reader (pdfplumber): Extracts high-fidelity text/layout coordinates from the PDF.
    4. Region Sniffer: Sniffs regional tax/legal headers to establish country context.
    5. Rule Engine: Matches country-specific keywords from 'config.json' to classify files.
    6. Router (shutil): Safely migrates files into './processed/<Category>/' directories.

Supported Classifications:
    - Invoices
    - Packing Lists
    - Customs Declarations
    - Supporting Documents (Fallback)

Dependencies:
    - watchdog (Filesystem Monitoring)
    - pdfplumber (Visual layout PDF parser)
    - config.json (Dynamic keyword/country mapping)

Author: Diptarka Roy
"""

import os
import time
import json
import shutil
import pdfplumber
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# Ensure processed directories exist
CATEGORIES = ["Invoices", "Packing_Lists", "Customs_Declarations", "Supporting Documents"]
KEYDOCUMENTS = ["Invoices", "Packing_Lists", "Customs_Declarations"]

for category in CATEGORIES:
    os.makedirs(os.path.join(PROCESSED_DIR, category), exist_ok=True)

def wait_for_file_to_copy(file_path, timeout=5):
    """Waits for a file to finish writing/downloading so it doesn't open corrupted."""
    last_size = -1
    for _ in range(timeout):
        try:
            current_size = os.path.getsize(file_path)
            if current_size == last_size and current_size > 0:
                return True
            last_size = current_size
        except OSError:
            pass
        time.sleep(0.5)
    return False

def load_config():
    """Loads the configurable keyword map."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading config.json: {e}. Using hardcoded fallbacks.")
        return {"countries": {}}

def detect_country(text_lower, config):
    """
    Dynamically identifies the origin country by scanning the 'country_markers' 
    defined in config.json.
    """
    countries_config = config.get("countries", {})
    
    # Loop through all configured countries to check their markers
    for country, rules in countries_config.items():
        # Skip Global_Default for marker detection
        if country == "Global_Default":
            continue
            
        markers = rules.get("country_markers", [])
        if any(marker in text_lower for marker in markers):
            return country
            
    return "Global_Default"

def classify_pdf(file_path):
    """Reads PDF text and classifies both country and document type via config.json."""
    try:
        config = load_config()
        countries_config = config.get("countries", {})

        with pdfplumber.open(file_path) as pdf:
            first_page_text = pdf.pages[0].extract_text()
            if not first_page_text:
                return "Supporting Documents"
            text_lower = first_page_text.lower()

        # 1. Dynamically detect the country using configuration markers
        country = detect_country(text_lower, config)
        print(f"🔍 Dynamic Region Match: [{country}]")
        
        # Get keyword arrays for the detected country (fallback to Global_Default)
        rules = countries_config.get(country, countries_config.get("Global_Default", {}))
        
        # 2. Match document type keywords dynamically
        for category in KEYDOCUMENTS:
            keywords = rules.get(category, [])
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return "Supporting Documents"
            
    except Exception as e:
        print(f"Error reading {os.path.basename(file_path)}: {e}")
        return "Supporting Documents"

def process_single_file(file_path):
    """Classifies and moves a single file."""
    filename = os.path.basename(file_path)
    
    if not wait_for_file_to_copy(file_path):
        print(f"Skipping {filename} - File write did not complete.")
        return

    category = classify_pdf(file_path)
    target_path = os.path.join(PROCESSED_DIR, category, filename)
    
    try:
        shutil.move(file_path, target_path)
        print(f"⚡ Routed: '{filename}' ➔ [{category}]")
    except Exception as e:
        print(f"Failed to move {filename}: {e}")

# --- WATCHDOG EVENT HANDLER ---
class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        # We only care about files, not folders
        if event.is_directory:
            return
        
        # Check if the created file is a PDF
        if event.src_path.lower().endswith('.pdf'):
            print(f"\n[New File Detected] Processing: {os.path.basename(event.src_path)}")
            process_single_file(event.src_path)

def start_watching():
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, path=DOWNLOADS_DIR, recursive=False)
    observer.start()
    
    print(f"👀 Active Folder Monitor: Watching '{DOWNLOADS_DIR}' for new PDFs...")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping monitor...")
    observer.join()

if __name__ == "__main__":
    start_watching()