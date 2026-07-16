"""
Module: main.py
Description: Primary orchestrator and entry point for the PDF Data Extractor Suite.
             Launches and coordinates the multi-threaded execution of the background 
             Gmail sync engine and the real-time local file system monitor.

Threading Architecture:
    - Thread 1 (Daemon Thread): Invokes the background polling loop from 'emails.py' 
      to periodically check Gmail, download filtered attachments, and mark emails as read.
    - Thread 2 (Main Thread): Runs the blocking 'watchdog' directory observer from 
      'classifier.py' to instantly capture, process, and route downloaded PDFs.

Execution:
    Run this script from the project root to start both engines simultaneously:
        $ python main.py

Dependencies:
    - threading (Standard Library)
    - src.emails (Gmail Sync Engine)
    - src.classifier (Filesystem Watcher & Classifier Engine)

Author: Diptarka Roy
"""

import threading
from dotenv import load_dotenv
from src.emails import email_checker_loop
from src.classifier import start_watching

load_dotenv()  # This automatically loads the .env file into your environment!

def main():
    print("🚀 Starting PDF Data Extractor Suite...")

    # 1. Start the Email Syncing loop (from emails.py) in a background thread
    email_thread = threading.Thread(target=email_checker_loop, daemon=True)
    email_thread.start()

    # 2. Start the Watchdog Folder Monitor (from classifier.py) on the main thread
    try:
        start_watching()
    except KeyboardInterrupt:
        print("\n👋 Shutting down suite. Goodbye!")

if __name__ == "__main__":
    main()